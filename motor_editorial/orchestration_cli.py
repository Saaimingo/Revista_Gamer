"""CLI surface for durable agent orchestration and opt-in SIWC integration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import uuid
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
    begin_login,
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
    probe.add_argument("--model", help="Slug visto em `siwc models`; padrão: primeiro modelo listado.")


def _json_payload(raw: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("O payload precisa ser um objeto JSON.")
    return value


def _dispatcher(queue: AgentQueue, *, siwc_client: SIWCClient | None = None) -> TaskDispatcher:
    executors: dict[str, Any] = {"simulated": SimulatedExecutor()}
    profiles = {
        (VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE,
        (SIWC_PROBE_PROFILE.profile_id, SIWC_PROBE_PROFILE.version): SIWC_PROBE_PROFILE,
    }
    if siwc_client is not None:
        executors["siwc-responses"] = SIWCExecutor(siwc_client, model=None)
    return TaskDispatcher(queue, executors=executors, profiles=profiles)


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
        model = args.model or str(visible[0]["slug"])
        if model not in {str(item["slug"]) for item in visible}:
            raise ValueError("O modelo informado não consta na lista visível desta conta.")
        queue = AgentQueue(store)
        task_id = queue.enqueue(
            task_type=SIWC_PROBE_TASK_TYPE,
            payload={"purpose": "single_non_editorial_integration_probe", "model": model},
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


def handle(args: argparse.Namespace, store: Any) -> int | None:
    if args.command == "agents":
        return _handle_agents(args, AgentQueue(store))
    if args.command == "scheduler":
        return _handle_scheduler(args, AgentQueue(store))
    if args.command == "siwc":
        return _handle_siwc(args, store)
    return None
