#!/bin/sh
# Run against this project's disposable local services; preserve volumes and reports.
set -eu
cd "$(dirname "$0")/.."
docker compose config --quiet
docker compose build --build-arg INSTALL_DEV=true
docker compose up --no-build --wait --wait-timeout 180
docker compose cp tests/. api:/app/tests
docker compose exec -T -e PGO_INTEGRATION=1 api python -m pytest /app/tests/integration/test_postgres.py /app/tests/integration/test_agent.py -v
(cd apps/web && npm run test:e2e)
# Process tests own the single worker lease and metrics port while the service is stopped.
restart_worker() { docker compose start worker; }
trap restart_worker EXIT
docker compose stop worker
docker compose exec -T -e PGO_INTEGRATION=1 -e PGO_RECOVERY=1 api python -m pytest /app/tests/integration/test_recovery.py -v
docker compose start worker
trap - EXIT
# This acceptance command never invokes a paid provider.
docker compose exec -T -e PGO_OPENAI_API_KEY= api pg-optimizer evaluate --output /app/experiments/reports/acceptance
mkdir -p experiments/reports/acceptance
docker compose cp api:/app/experiments/reports/acceptance/. experiments/reports/acceptance
docker compose exec -T api python - <<'PY'
import json
from pathlib import Path

results = json.loads(Path("/app/experiments/reports/acceptance/evaluation.json").read_text())
deterministic = [item for item in results if item["provider"] == "deterministic"]
assert len(deterministic) == 12, "Evaluation must cover all twelve deterministic workloads"
assert all(item["session"]["status"] == "completed" for item in deterministic), "Evaluation failed"
assert all(item["status"] == "not_run" for item in results if item["provider"] == "openai")
print("All twelve deterministic evaluations completed; model evaluation not run")
PY
