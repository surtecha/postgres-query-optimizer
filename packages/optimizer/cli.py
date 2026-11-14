import argparse
import json
import time
from pathlib import Path
from typing import Any

from optimizer.config import Settings
from optimizer.database import Database
from optimizer.dataset import generate
from optimizer.evaluation_metrics import aggregate
from optimizer.persistence import Store
from optimizer.statistics import summary
from optimizer.workloads import WORKLOADS


def evaluate(settings: Settings, output: Path, identifiers: list[str]) -> None:
    db = Database(settings)
    store = Store(settings.app_dsn.get_secret_value())
    db.open()
    results: list[dict[str, Any]] = []
    try:
        for workload in WORKLOADS:
            if identifiers and workload["id"] not in identifiers:
                continue
            with db.experiment_lock():
                with db.reader() as conn:
                    db.timed(conn, workload["sql"])
                    baseline = [
                        db.timed(conn, workload["sql"])[0] for _ in range(settings.repetitions)
                    ]
                environment = db.inspect(workload["sql"])
            for provider in ("deterministic", "openai"):
                if provider == "openai" and not settings.openai_api_key.get_secret_value():
                    results.append(
                        {
                            "workload_id": workload["id"],
                            "provider": provider,
                            "status": "not_run",
                            "reason": "No model credential configured",
                        }
                    )
                    continue
                identifier = store.create(
                    {"sql": workload["sql"], "provider": provider, "workload_id": workload["id"]},
                    None,
                    settings.max_pending,
                )
                deadline = time.monotonic() + settings.session_seconds + 60
                while time.monotonic() < deadline:
                    session = store.get(identifier)
                    if session and session["status"] not in ("queued", "running"):
                        break
                    time.sleep(0.5)
                else:
                    store.cancel(identifier)
                    session = {"status": "evaluation_timeout"}
                results.append(
                    {
                        "workload_id": workload["id"],
                        "provider": provider,
                        "original_baseline": summary(baseline),
                        "environment": environment,
                        "session": session,
                    }
                )
                output.mkdir(parents=True, exist_ok=True)
                (output / "evaluation.json").write_text(json.dumps(results, indent=2, default=str))
        output.mkdir(parents=True, exist_ok=True)
        (output / "evaluation.json").write_text(json.dumps(results, indent=2, default=str))
        (output / "summary.json").write_text(json.dumps(aggregate(results), indent=2, default=str))
        lines = [
            "# Evaluation",
            "",
            "Real measurements only. Missing provider runs remain not_run.",
            "",
            "| Workload | Provider | Status | Best paired speedup |",
            "|---|---|---|---|",
        ]
        for item in results:
            session = item.get("session", {})
            report = session.get("report") or {}
            accepted = [c for c in report.get("candidates", []) if c.get("accepted")]
            speedup = max((c["benchmark"]["median_speedup"] for c in accepted), default=None)
            lines.append(
                f"| {item['workload_id']} | {item['provider']} | "
                f"{item.get('status', session.get('status'))} | "
                f"{speedup if speedup else 'none'} |"
            )
        (output / "evaluation.md").write_text("\n".join(lines) + "\n")
    finally:
        db.close()
        store.engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="pg-optimizer")
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed")
    seed.add_argument("--size", choices=["small", "medium", "large"], default="small")
    seed.add_argument("--seed", type=int, default=42)
    seed.add_argument("--if-empty", action="store_true")
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--output", type=Path, default=Path("experiments/reports/latest"))
    evaluation.add_argument("--workloads", nargs="*", default=[])
    commands.add_parser("worker")
    args = parser.parse_args()
    settings = Settings()
    if args.command == "seed":
        if args.if_empty:
            import psycopg

            with psycopg.connect(settings.admin_dsn.get_secret_value()) as conn:
                relation = conn.execute(
                    "SELECT to_regclass('commerce.dataset_manifest')"
                ).fetchone()
                if relation is not None and relation[0]:
                    manifest = conn.execute(
                        "SELECT count(*) FROM commerce.dataset_manifest"
                    ).fetchone()
                    if manifest is not None and manifest[0]:
                        return
        generate(
            settings.admin_dsn.get_secret_value(), args.size, args.seed, Path("datasets/schema.sql")
        )
    elif args.command == "evaluate":
        evaluate(settings, args.output, args.workloads)
    else:
        from optimizer.worker import run

        run()


if __name__ == "__main__":
    main()
