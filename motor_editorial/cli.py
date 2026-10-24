"""Command-line interface for the local simulation."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .db import Store
from .domain import MotorError
from .workflow import APPROVAL_PHRASE, EXCLUSION_PHRASE, Motor
from .web import serve
from .orchestration import TaskFailure
from .orchestration_cli import add_commands as add_orchestration_commands
from .orchestration_cli import handle as handle_orchestration_command
from .siwc import SIWCError


DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "runtime"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="motor_editorial",
        description="Motor Editorial v0.2 — simulador multipauta local e offline.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Pasta local para banco, prévias e arquivos de execução.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Criar ou abrir o banco SQLite local.")
    commands.add_parser("demo", help="Executar ou retomar a demonstração fictícia multipauta v0.2.")
    commands.add_parser("demo-v1", help="Executar a fixture de compatibilidade do Motor Editorial v0.1.")
    layout_demo = commands.add_parser(
        "layout-demo", help="Executar a simulação offline do diagramador e da composição."
    )
    layout_demo.add_argument(
        "--fixture", type=Path, default=None,
        help="Fixture JSON local; por padrão usa os três cenários sintéticos da Fase 0.",
    )
    run_story = commands.add_parser("run-story", help="Retomar somente uma pauta multipauta.")
    run_story.add_argument("run_id")
    run_story.add_argument("story_id")
    commands.add_parser("status", help="Mostrar estados, execuções e tentativas.")
    approve = commands.add_parser("approve", help="Registrar aprovação humana interna.")
    approve.add_argument("edition_id", help="Identificador da edição em espera.")
    exclude = commands.add_parser("exclude", help="Registrar exclusão humana de pauta da edição.")
    exclude.add_argument("edition_id")
    exclude.add_argument("story_id")
    commands.add_parser("web", help="Abrir o painel local em 127.0.0.1.").add_argument(
        "--port", type=int, default=8765, help="Porta local (padrão: 8765)."
    )
    add_orchestration_commands(commands)
    return parser


def _open_motor(data_dir: Path) -> Motor:
    data_dir = data_dir.expanduser().resolve()
    store = Store(data_dir / "motor.sqlite3", data_dir / "artifacts")
    return Motor(store)


def _status_payload(motor: Motor) -> dict[str, object]:
    dashboard = motor.store.dashboard()
    run = dashboard["run"]
    return {
        "counts": motor.store.counts(),
        "run": dict(run) if run else None,
        "stories": [
            {"id": row["id"], "state": row["state"],
             "processing_status": row["processing_status"], "question": row["question"]}
            for row in dashboard["stories"]
        ],
        "editions": [
            {"id": row["id"], "status": row["status"],
             "composition_status": row["composition_status"],
             "preview_path": row["preview_path"]}
            for row in dashboard["editions"]
        ],
        "edition_memberships": [
            {"edition_id": row["edition_id"], "story_id": row["story_id"],
             "position": row["position"], "active": row["active"],
             "required": row["required"], "state": row["state"],
             "exclusion_reason": row["exclusion_reason"]}
            for row in dashboard["edition_memberships"]
        ],
        "recent_attempts": [
            {"stage": row["stage"], "attempt_number": row["attempt_number"], "status": row["status"], "error": row["error_summary"]}
            for row in dashboard["attempts"]
        ],
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        motor = _open_motor(args.data_dir)
        if args.command == "init":
            print(f"Banco local pronto: {motor.store.db_path}")
            return 0
        if args.command in {"demo", "demo-v1"}:
            result = motor.run_multipauta_demo() if args.command == "demo" else motor.run_demo()
            print(json.dumps({
                "run_id": result.run_id,
                "status": result.status,
                "message": result.message,
                "edition_id": result.edition_id,
                "counts": motor.store.counts(),
            }, ensure_ascii=False, indent=2))
            return 2 if result.status == "failed_intervention" else 0
        if args.command == "layout-demo":
            report = motor.run_layout_demo(args.fixture)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["status"] == "awaiting_approval" else 2
        if args.command == "run-story":
            result = motor.run_multipauta_story(args.run_id, args.story_id)
            print(json.dumps({
                "run_id": result.run_id, "status": result.status,
                "message": result.message, "edition_id": result.edition_id,
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "status":
            print(json.dumps(_status_payload(motor), ensure_ascii=False, indent=2))
            return 0
        if args.command == "approve":
            if not sys.stdin.isatty():
                print("A aprovação exige uma sessão interativa no terminal.", file=sys.stderr)
                return 2
            actor = input("Nome/identificação do diretor ou aprovador: ").strip()
            confirmation = input(f"Digite {APPROVAL_PHRASE}: ").strip()
            motor.approve_internally(args.edition_id, actor, confirmation)
            print("Aprovação interna registrada. Nada foi publicado.")
            return 0
        if args.command == "exclude":
            if not sys.stdin.isatty():
                print("A exclusão exige uma sessão interativa no terminal.", file=sys.stderr)
                return 2
            actor = input("Nome/identificação de quem decide: ").strip()
            reason = input("Motivo editorial da exclusão: ").strip()
            confirmation = input(f"Digite {EXCLUSION_PHRASE}: ").strip()
            motor.exclude_story_from_edition(
                args.edition_id, args.story_id, actor, reason, confirmation
            )
            print("Exclusão interna auditada. A pauta permanece no histórico.")
            return 0
        if args.command == "web":
            if not 0 <= args.port <= 65535:
                print("A porta deve estar entre 0 e 65535.", file=sys.stderr)
                return 2
            serve(motor, args.port)
            return 0
        orchestration_status = handle_orchestration_command(args, motor.store)
        if orchestration_status is not None:
            return orchestration_status
    except TaskFailure as error:
        print(f"Erro [{error.code}]: {error.summary}", file=sys.stderr)
        return 2
    except (MotorError, SIWCError, OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
