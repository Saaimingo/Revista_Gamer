"""CLI surface for durable agent orchestration and opt-in SIWC integration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .orchestration import (
    AgentQueue,
    SimulatedExecutor,
    SchedulerWorker,
    TaskDispatcher,
    VALIDATION_PROFILE,
    run_simulated_chain,
)
from .siwc import (
    CredentialStore,
    SIWCClient,
    SIWCError,
    SIWCExecutor,
    SIWC_PROBE_PROFILE,
    SIWC_PROBE_TASK_TYPE,
    SIWC_REASONING_EFFORTS,
    begin_login,
)
from .editorial import (
    EDITORIAL_EXECUTOR_ID,
    EDITORIAL_MODEL,
    EDITORIAL_PROFILE,
    EDITORIAL_REASONING_EFFORT,
    EDITORIAL_STAGES,
    STAGE_DEPENDENCIES,
    EDITORIAL_TASK_TYPE,
    SIWCEditorialExecutor,
    WORD_TARGETS,
    normalize_source_packet,
    review_matches_revision,
)


PLUS_SCHEDULE_CONFIRMATION = "AUTORIZO CHAMADAS PLUS AGENDADAS"


def add_commands(commands: argparse._SubParsersAction) -> None:
    agents = commands.add_parser("agents", help="Fila durável, dispatcher e execuções simuladas.")
    agent_commands = agents.add_subparsers(dest="agents_command", required=True)
    agent_commands.add_parser("demo-chain", help="Provar uma cadeia de agentes inteiramente simulados.")
    enqueue = agent_commands.add_parser("enqueue", help="Adicionar tarefa técnica à fila SQLite.")
    enqueue.add_argument("task_type")
    enqueue.add_argument("--payload", required=True, help="Objeto JSON da tarefa.")
    enqueue.add_argument("--idempotency-key", required=True)
    enqueue.add_argument("--executor", default="simulated", choices=["simulated"])
    enqueue.add_argument("--profile", default="validation")
    enqueue.add_argument("--max-attempts", type=int, default=3)
    agent_commands.add_parser("work-once", help="Executar no máximo uma tarefa simulada pronta.")
    task_list = agent_commands.add_parser("list", help="Listar estados sem expor payloads ou tokens.")
    task_list.add_argument("--limit", type=int, default=50)
    events = agent_commands.add_parser("events", help="Exibir eventos sem payload ou credenciais.")
    events.add_argument("task_id")

    scheduler = commands.add_parser("scheduler", help="Configurar ou executar o polling de agendas.")
    scheduler_commands = scheduler.add_subparsers(dest="scheduler_command", required=True)
    schedule_add = scheduler_commands.add_parser("add", help="Criar agenda desativada.")
    schedule_add.add_argument("schedule_id")
    schedule_add.add_argument("task_type")
    schedule_add.add_argument("--payload", required=True, help="Objeto JSON da tarefa.")
    schedule_add.add_argument("--executor", default="simulated", choices=["simulated", "siwc-responses"])
    schedule_add.add_argument("--interval-seconds", type=int, required=True)
    schedule_add.add_argument("--timezone", default="UTC")
    schedule_add.add_argument("--misfire", choices=["skip", "run_once"], default="skip")
    schedule_commands = scheduler_commands
    schedule_commands.add_parser("list", help="Listar agendas e estados.")
    toggle = schedule_commands.add_parser("enable", help="Ativar agenda com confirmação explícita.")
    toggle.add_argument("schedule_id")
    toggle.add_argument("--confirm", default="")
    disable = schedule_commands.add_parser("disable", help="Desativar uma agenda.")
    disable.add_argument("schedule_id")
    scheduler_run = scheduler_commands.add_parser("run", help="Executar o worker contínuo de agendas.")
    scheduler_run.add_argument("--poll-seconds", type=float, default=2.0)
    scheduler_run.add_argument("--max-cycles", type=int)

    siwc = commands.add_parser("siwc", help="Autenticação oficial opcional e prova SIWC não editorial.")
    siwc_commands = siwc.add_subparsers(dest="siwc_command", required=True)
    login = siwc_commands.add_parser("login", help="Abrir fluxo OAuth oficial com callback loopback local.")
    login.add_argument("--timeout-seconds", type=int, default=900)
    siwc_commands.add_parser("status", help="Mostrar estado local sem divulgar tokens ou identidade.")
    siwc_commands.add_parser("models", help="Consultar modelos listados para a conta autorizada.")
    probe = siwc_commands.add_parser("probe", help="Fazer uma única inferência técnica sintética.")
    probe.add_argument("--model", required=True, help="Slug exato visto em `siwc models`; sem seleção automática.")
    probe.add_argument(
        "--reasoning-effort", required=True, choices=sorted(SIWC_REASONING_EFFORTS),
        help="Esforço explicitamente solicitado e conferido no objeto Responses concluído.",
    )

    editorial = commands.add_parser("editorial", help="Experimento editorial local com fonte e revisão humana obrigatórias.")
    editorial_commands = editorial.add_subparsers(dest="editorial_command", required=True)
    editorial_run = editorial_commands.add_parser("run", help="Executar o pipeline limitado de uma matéria sem publicar.")
    editorial_run.add_argument("--packet", required=True, type=Path, help="JSON pesquisado e estruturado com fontes.")
    editorial_run.add_argument("--run-id", help="UUID para retomar os checkpoints do mesmo pacote e da mesma execução.")
    editorial_run.add_argument(
        "--source-collection-duration-ms", type=int,
        help="Duração medida da pesquisa/coleta manual de fontes; não inclui inferência.",
    )


def _json_payload(raw: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("O payload precisa ser um objeto JSON.")
    return value


def _dispatcher(
    queue: AgentQueue,
    *,
    siwc_client: SIWCClient | None = None,
    editorial_catalog_models: set[str] | None = None,
) -> TaskDispatcher:
    executors: dict[str, Any] = {"simulated": SimulatedExecutor()}
    profiles = {
        (VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE,
        (SIWC_PROBE_PROFILE.profile_id, SIWC_PROBE_PROFILE.version): SIWC_PROBE_PROFILE,
        (EDITORIAL_PROFILE.profile_id, EDITORIAL_PROFILE.version): EDITORIAL_PROFILE,
    }
    if siwc_client is not None:
        executors["siwc-responses"] = SIWCExecutor(siwc_client, model=None)
        executors[EDITORIAL_EXECUTOR_ID] = SIWCEditorialExecutor(
            siwc_client, catalog_models=editorial_catalog_models
        )
    return TaskDispatcher(queue, executors=executors, profiles=profiles)


def _editorial_run(args: argparse.Namespace, store: Any) -> int:
    process_started_at = datetime.now(timezone.utc)
    process_started_clock = time.monotonic()
    packet_started_clock = time.monotonic()
    raw_packet = json.loads(args.packet.read_text(encoding="utf-8"))
    packet = normalize_source_packet(raw_packet)
    packet_validation_duration_ms = round((time.monotonic() - packet_started_clock) * 1000, 3)
    source_collection_duration_ms = getattr(args, "source_collection_duration_ms", None)
    if source_collection_duration_ms is not None and (
        isinstance(source_collection_duration_ms, bool)
        or not isinstance(source_collection_duration_ms, int)
        or source_collection_duration_ms < 0
    ):
        raise ValueError("A duração da coleta de fontes precisa ser um inteiro não negativo em milissegundos.")
    run_id = str(uuid.UUID(args.run_id)) if args.run_id else str(uuid.uuid4())

    # A run_id is bound to its immutable profile version. Never replay old
    # checkpoints under changed prompts or reuse a review of stale text.
    with closing(store.connect()) as connection:
        prior_versions = {
            row["profile_version"] for row in connection.execute(
                """SELECT DISTINCT profile_version FROM agent_tasks
                   WHERE task_type = ? AND idempotency_key LIKE ?""",
                (EDITORIAL_TASK_TYPE, f"editorial:{run_id}:%"),
            ).fetchall()
        }
    incompatible = prior_versions - {EDITORIAL_PROFILE.version}
    if incompatible:
        raise ValueError(
            "Esta run_id tem checkpoints do perfil " + ", ".join(sorted(incompatible))
            + "; use uma nova run_id para executar o perfil " + EDITORIAL_PROFILE.version + "."
        )

    queue = AgentQueue(store)
    client = SIWCClient(CredentialStore())
    visible = {
        str(item["slug"]) for item in client.models()
        if item.get("visibility") == "list"
    }
    if EDITORIAL_MODEL not in visible:
        raise SIWCError(
            "editorial_model_not_in_account_catalog",
            "gpt-6-luna não aparece no catálogo atual desta conta; nenhuma etapa editorial foi executada.",
        )
    catalog_request_metrics = getattr(client, "last_models_request_metrics", None)
    catalog_metrics = {
        "model": EDITORIAL_MODEL,
        "request_count": 1,
        "duration_instrumented": isinstance(catalog_request_metrics, dict),
        "last_request": catalog_request_metrics,
    }
    dispatcher = _dispatcher(
        queue, siwc_client=client, editorial_catalog_models=visible
    )

    outputs: dict[str, Any] = {}
    stage_rows: list[dict[str, Any]] = []
    execution_status = "incomplete"
    editorial_status = "blocked"
    human_approval_status = "not_reached"
    for stage in EDITORIAL_STAGES:
        payload = {
            "run_id": run_id,
            "stage": stage,
            "packet": packet,
            "previous_outputs": {
                dependency: outputs[dependency]
                for dependency in STAGE_DEPENDENCIES[stage]
                if dependency in outputs
            },
            "model": EDITORIAL_MODEL,
            "reasoning_effort": EDITORIAL_REASONING_EFFORT,
        }
        task_id = queue.enqueue(
            task_type=EDITORIAL_TASK_TYPE, payload=payload,
            profile=EDITORIAL_PROFILE, executor_id=EDITORIAL_EXECUTOR_ID,
            idempotency_key=f"editorial:{run_id}:{stage}", max_attempts=1,
        )
        task = queue.get(task_id)
        if task is None:
            raise RuntimeError("Checkpoint editorial desapareceu da fila SQLite.")
        if task.state != "succeeded":
            dispatcher.dispatch_one(task_id)
            task = queue.get(task_id)
        state = task.state if task else "missing"
        result = task.result if task else None
        events = queue.events(task_id)
        stage_output = result.get("structured_output") if result else None
        stage_rows.append({
            "stage": stage, "task_id": task_id, "state": state,
            "model": result.get("model") if result else None,
            "reasoning_effort": result.get("reasoning_effort") if result else None,
            "request_started_at": result.get("request_started_at") if result else None,
            "completed_at": result.get("completed_at") if result else None,
            "duration_ms": result.get("duration_ms") if result else None,
            "usage": result.get("usage") if result else None,
            "revision_sha256": (
                stage_output.get("reviewed_revision_sha256")
                or stage_output.get("checked_revision_sha256")
                if isinstance(stage_output, dict) else None
            ),
            "error_code": (
                events[-1]["detail"].get("error_code")
                if task and task.state not in {"succeeded", "running", "queued", "retry_wait"}
                and events else None
            ),
        })
        if state != "succeeded" or not result or not isinstance(stage_output, dict):
            execution_status = "incomplete"
            editorial_status = "blocked"
            break
        outputs[stage] = stage_output

        if stage == "review":
            draft = outputs["draft"]
            review = outputs["review"]
            if not review_matches_revision(review, draft):
                execution_status = "completed"
                editorial_status = "blocked_human_decision"
                human_approval_status = "human_action_required_stale_review"
                break
            if review["verdict"] == "hold":
                execution_status = "completed"
                editorial_status = "blocked_human_decision"
                human_approval_status = "human_action_required_hold"
                break
            if review["verdict"] == "pass":
                execution_status = "completed"
                editorial_status = "awaiting_human_approval"
                human_approval_status = "pending"
                break

        if stage == "final_review":
            corrected = outputs["correction"]
            final_review = outputs["final_review"]
            if not review_matches_revision(final_review, corrected):
                editorial_status = "blocked_human_decision"
                human_approval_status = "human_action_required_stale_review"
            elif final_review["verdict"] == "pass":
                editorial_status = "awaiting_human_approval"
                human_approval_status = "pending"
            else:
                editorial_status = "blocked_human_decision"
                human_approval_status = "human_action_required_review"
            execution_status = "completed"
            break

    final_output = outputs.get("correction") or outputs.get("draft")
    final_body = str(final_output.get("body_markdown", "")) if isinstance(final_output, dict) else ""
    final_word_count = len(final_body.split()) if final_body else None
    word_target = WORD_TARGETS[packet["article_type"]]
    length_target_met = (
        final_word_count is not None and word_target[0] <= final_word_count <= word_target[1]
    )
    finished_at = datetime.now(timezone.utc)
    final_review = outputs.get("final_review") or outputs.get("review")
    reviewed_revision_sha256 = (
        final_review.get("reviewed_revision_sha256")
        if isinstance(final_review, dict) else None
    )
    current_review_matches_final_article = (
        isinstance(final_review, dict)
        and isinstance(final_output, dict)
        and review_matches_revision(final_review, final_output)
    )
    article_readiness = (
        "below_target" if not length_target_met else
        "pending_human_approval" if editorial_status == "awaiting_human_approval" else
        "human_decision_required"
    )
    duration_ms = round((time.monotonic() - process_started_clock) * 1000, 3)
    usage_totals: dict[str, int] = {}
    for row in stage_rows:
        usage = row.get("usage")
        if not isinstance(usage, dict):
            continue
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            if isinstance(usage.get(field), int):
                usage_totals[field] = usage_totals.get(field, 0) + usage[field]
        details = usage.get("output_tokens_details")
        if isinstance(details, dict) and isinstance(details.get("reasoning_tokens"), int):
            usage_totals["reasoning_tokens"] = usage_totals.get("reasoning_tokens", 0) + details["reasoning_tokens"]
        details = usage.get("input_tokens_details")
        if isinstance(details, dict):
            for field in ("cached_tokens", "cache_write_tokens"):
                if isinstance(details.get(field), int):
                    usage_totals[field] = usage_totals.get(field, 0) + details[field]
    report = {
        "run_id": run_id,
        "state": editorial_status,
        "execution_status": execution_status,
        "editorial_status": editorial_status,
        "human_approval_status": human_approval_status,
        "sample_classification": "technical_sample",
        "article_readiness": article_readiness,
        "ready_for_publication": False,
        "started_at": process_started_at.isoformat(timespec="milliseconds"),
        "completed_at": finished_at.isoformat(timespec="milliseconds"),
        "duration_ms": duration_ms,
        "source_collection_duration_ms": source_collection_duration_ms,
        "source_packet_validation_duration_ms": packet_validation_duration_ms,
        "catalog": catalog_metrics,
        "model": EDITORIAL_MODEL,
        "reasoning_effort": EDITORIAL_REASONING_EFFORT,
        "executor_id": EDITORIAL_EXECUTOR_ID,
        "profile_id": EDITORIAL_PROFILE.profile_id,
        "profile_version": EDITORIAL_PROFILE.version,
        "profile_sha256": EDITORIAL_PROFILE.content_hash,
        "article_type": packet["article_type"],
        "topic": packet["topic"],
        "source_count": len(packet["sources"]),
        "source_ids": [source["id"] for source in packet["sources"]],
        "usage_totals": usage_totals,
        "reasoning_tokens_are_subset_of_output_tokens": True,
        "stages": stage_rows,
        "outputs": outputs,
        "final_article": final_output,
        "word_count": final_word_count,
        "word_target_range": list(word_target),
        "length_target_met": length_target_met,
        "reviewed_revision_sha256": reviewed_revision_sha256,
        "current_review_matches_final_article": current_review_matches_final_article,
        "human_review_required": True,
        "publication_state": "not_published",
    }
    artifact_dir = Path(store.artifact_dir) / "codex004"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{run_id}.json"
    artifact_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "run_id": run_id, "state": editorial_status,
        "execution_status": execution_status,
        "editorial_status": editorial_status,
        "human_approval_status": human_approval_status,
        "sample_classification": "technical_sample",
        "article_readiness": article_readiness,
        "ready_for_publication": False,
        "artifact": str(artifact_path),
        "model": EDITORIAL_MODEL, "reasoning_effort": EDITORIAL_REASONING_EFFORT,
        "executor_id": EDITORIAL_EXECUTOR_ID,
        "profile_id": EDITORIAL_PROFILE.profile_id,
        "profile_version": EDITORIAL_PROFILE.version,
        "profile_sha256": EDITORIAL_PROFILE.content_hash,
        "calls_completed": sum(1 for row in stage_rows if row["state"] == "succeeded"),
        "calls_attempted": len(stage_rows), "usage_totals": usage_totals,
        "reasoning_tokens_are_subset_of_output_tokens": True,
        "catalog": catalog_metrics,
        "source_collection_duration_ms": source_collection_duration_ms,
        "source_packet_validation_duration_ms": packet_validation_duration_ms,
        "word_count": final_word_count, "word_target_range": list(word_target),
        "length_target_met": length_target_met,
        "reviewed_revision_sha256": reviewed_revision_sha256,
        "current_review_matches_final_article": current_review_matches_final_article,
        "stages": stage_rows, "human_review_required": True,
        "publication_state": "not_published",
    }, ensure_ascii=False, indent=2))
    return 0 if execution_status == "completed" else 2

def _handle_agents(args: argparse.Namespace, queue: AgentQueue) -> int:
    if args.agents_command == "demo-chain":
        print(json.dumps(run_simulated_chain(queue), ensure_ascii=False, indent=2))
        return 0
    if args.agents_command == "enqueue":
        if args.profile != "validation":
            raise ValueError("Somente o perfil interno de validação está configurado nesta etapa.")
        task_id = queue.enqueue(
            task_type=args.task_type, payload=_json_payload(args.payload),
            profile=VALIDATION_PROFILE, executor_id=args.executor,
            idempotency_key=args.idempotency_key, max_attempts=args.max_attempts,
        )
        print(json.dumps({"task_id": task_id, "state": queue.get(task_id).state}, indent=2))
        return 0
    if args.agents_command == "work-once":
        result = _dispatcher(queue).dispatch_one()
        print(json.dumps({"task_id": result.task_id, "state": result.state,
                          "error_code": result.error_code}, ensure_ascii=False, indent=2))
        return 0 if result.state in {"idle", "succeeded"} else 2
    if args.agents_command == "list":
        print(json.dumps([{
            "task_id": task.task_id, "task_type": task.task_type,
            "profile_id": task.profile_id, "profile_version": task.profile_version,
            "executor_id": task.executor_id, "state": task.state,
            "attempts": task.attempts, "max_attempts": task.max_attempts,
            "available_at": task.available_at,
        } for task in queue.list_tasks(args.limit)], ensure_ascii=False, indent=2))
        return 0
    if args.agents_command == "events":
        print(json.dumps(queue.events(args.task_id), ensure_ascii=False, indent=2))
        return 0
    return 2


def _handle_scheduler(args: argparse.Namespace, queue: AgentQueue) -> int:
    if args.scheduler_command == "add":
        if args.executor == "siwc-responses":
            profile = SIWC_PROBE_PROFILE
        else:
            profile = VALIDATION_PROFILE
        queue.create_schedule(
            schedule_id=args.schedule_id, task_type=args.task_type,
            payload=_json_payload(args.payload), profile=profile,
            executor_id=args.executor, interval_seconds=args.interval_seconds,
            timezone_name=args.timezone, misfire_policy=args.misfire, enabled=False,
        )
        print(json.dumps({"schedule_id": args.schedule_id, "enabled": False}, indent=2))
        return 0
    if args.scheduler_command == "list":
        print(json.dumps(queue.list_schedules(), ensure_ascii=False, indent=2))
        return 0
    if args.scheduler_command == "disable":
        queue.set_schedule_enabled(args.schedule_id, False)
        print(json.dumps({"schedule_id": args.schedule_id, "enabled": False}, indent=2))
        return 0
    if args.scheduler_command == "enable":
        schedules = {row["id"]: row for row in queue.list_schedules()}
        schedule = schedules.get(args.schedule_id)
        if schedule is None:
            raise ValueError("Agenda inexistente.")
        if schedule["executor_id"] == "siwc-responses" and args.confirm != PLUS_SCHEDULE_CONFIRMATION:
            raise ValueError(
                "Ativar chamadas Plus recorrentes exige --confirm "
                f"\"{PLUS_SCHEDULE_CONFIRMATION}\" e uma decisão operacional específica."
            )
        queue.set_schedule_enabled(args.schedule_id, True)
        print(json.dumps({"schedule_id": args.schedule_id, "enabled": True}, indent=2))
        return 0
    if args.scheduler_command == "run":
        schedules = queue.list_schedules()
        siwc_scheduled = any(
            row["enabled"] and row["executor_id"] == "siwc-responses" for row in schedules
        )
        siwc_client = None
        if siwc_scheduled:
            if os.environ.get("MOTOR_EDITORIAL_ALLOW_PLUS_SCHEDULING") != "1":
                raise ValueError(
                    "Agendas Plus estão habilitadas, mas o worker exige "
                    "MOTOR_EDITORIAL_ALLOW_PLUS_SCHEDULING=1 definido pelo operador."
                )
            siwc_client = SIWCClient(CredentialStore())
        dispatcher = _dispatcher(queue, siwc_client=siwc_client)
        worker = SchedulerWorker(
            queue, dispatcher, poll_seconds=args.poll_seconds,
            on_tick=lambda created, outcome: print(json.dumps({
                "enqueued": created, "task_id": outcome.task_id,
                "state": outcome.state, "error_code": outcome.error_code,
            }, ensure_ascii=False), flush=True),
        )
        try:
            worker.run(stop_event=threading.Event(), max_cycles=args.max_cycles)
        except KeyboardInterrupt:
            return 130
        return 0
    return 2


def _handle_siwc(args: argparse.Namespace, store: Any) -> int:
    credentials = CredentialStore()
    if args.siwc_command == "login":
        result = begin_login(
            credentials,
            show_authorization_url=lambda url: print(
                "Abra este link de autorização OpenAI no navegador usado para sua conta ChatGPT:\n" + url,
                flush=True,
            ),
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.siwc_command == "status":
        with credentials.lock():
            record = credentials.load()
        if not record:
            print(json.dumps({"authenticated": False, "direct_usage_scope": False}, indent=2))
            return 0
        print(json.dumps({
            "authenticated": True,
            "direct_usage_scope": "chatgpt.tokens.use.direct" in record.get("scopes", []),
            "expires_at_epoch": record.get("expires_at"),
            "client_id_suffix": str(record.get("client_id", ""))[-8:],
            "host_id": record.get("host_id"),
            "scopes": record.get("scopes", []),
        }, ensure_ascii=False, indent=2))
        return 0
    client = SIWCClient(credentials)
    if args.siwc_command == "models":
        models = client.models()
        print(json.dumps([
            {"slug": item["slug"], "display_name": item["display_name"]}
            for item in models if item.get("visibility") == "list"
        ], ensure_ascii=False, indent=2))
        return 0
    if args.siwc_command == "probe":
        visible = [item for item in client.models() if item.get("visibility") == "list"]
        if not visible:
            raise SIWCError("no_models_available", "A conta não retornou modelos listados para uso.")
        model = str(args.model).strip()
        if model not in {str(item["slug"]) for item in visible}:
            raise ValueError("O modelo informado não consta na lista visível desta conta.")
        reasoning_effort = str(args.reasoning_effort)
        queue = AgentQueue(store)
        task_id = queue.enqueue(
            task_type=SIWC_PROBE_TASK_TYPE,
            payload={
                "purpose": "single_non_editorial_integration_probe",
                "model": model,
                "reasoning_effort": reasoning_effort,
            },
            profile=SIWC_PROBE_PROFILE,
            executor_id="siwc-responses",
            idempotency_key=f"siwc-probe:{uuid.uuid4()}",
            max_attempts=1,
        )
        outcome = _dispatcher(queue, siwc_client=client).dispatch_one(task_id)
        task = queue.get(task_id)
        payload = {
            "task_id": task_id, "state": outcome.state,
            "error_code": outcome.error_code,
            "result": task.result if task else None,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if outcome.state == "succeeded" else 2
    return 2


def _handle_editorial(args: argparse.Namespace, store: Any) -> int:
    if args.editorial_command == "run":
        return _editorial_run(args, store)
    return 2


def handle(args: argparse.Namespace, store: Any) -> int | None:
    if args.command == "agents":
        return _handle_agents(args, AgentQueue(store))
    if args.command == "scheduler":
        return _handle_scheduler(args, AgentQueue(store))
    if args.command == "siwc":
        return _handle_siwc(args, store)
    if args.command == "editorial":
        return _handle_editorial(args, store)
    return None
