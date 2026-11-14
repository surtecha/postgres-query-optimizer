#!/bin/sh
# Runs only deterministic and local Ollama arms. Never selects a paid provider.
set -eu
cd "$(dirname "$0")/.."
model=${PGO_OLLAMA_MODEL:-qwen2.5-coder:3b}
export PGO_OLLAMA_MODEL="$model"
export PGO_MAX_MODEL_TOKENS=${PGO_MAX_MODEL_TOKENS:-32000}
export PGO_OPENAI_API_KEY=
output=experiments/reports/ollama
mkdir -p "$output"
docker compose config --quiet
docker info >/dev/null
docker compose build api worker
# Reuse a running host Ollama server; otherwise start the optional container.
if curl -fsS --max-time 3 http://localhost:11434/api/version >"$output/ollama-version.json"; then
  export PGO_OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
else
  export PGO_OLLAMA_BASE_URL=http://ollama:11434/v1
  docker compose --profile local-llm up -d --wait ollama
  curl -fsS --max-time 10 http://localhost:11434/api/version >"$output/ollama-version.json"
fi
# JSON encoding avoids interpreting a model name as shell syntax.
model_payload=$(docker compose run --rm --no-deps -T api python -c \
  'import json, os; print(json.dumps({"model": os.environ["PGO_OLLAMA_MODEL"], "stream": False}))')
curl -fsS --max-time 1800 http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' -d "$model_payload" >"$output/model-pull.json"
curl -fsS --max-time 30 http://localhost:11434/api/show \
  -H 'Content-Type: application/json' -d "$model_payload" >"$output/model-info.json"
curl -fsS --max-time 10 http://localhost:11434/api/tags >"$output/model-tags.json"
docker compose up -d --build --wait
# Validate an actual model response from inside the worker network before evaluation.
docker compose exec -T worker python - >"$output/model-smoke.json" <<'PY'
import json
from optimizer.config import Settings
from optimizer.providers import OllamaProvider

candidates, usage = OllamaProvider(Settings()).generate("SELECT 1", {}, 1)
# Write diagnostics even when inference or schema validation fails.
print(json.dumps({**usage, "candidates": len(candidates)}), flush=True)
if "error" in usage or usage.get("calls") != 1:
    raise SystemExit(
        "Ollama smoke check failed; inspect experiments/reports/ollama/model-smoke.json"
    )
PY
docker compose exec -T api pg-optimizer evaluate \
  --providers deterministic ollama --output /app/experiments/reports/ollama "$@"
docker compose cp api:/app/experiments/reports/ollama/. "$output"
# A completed session alone is insufficient: fallback-only runs cannot pass.
docker compose exec -T api python - <<'PY'
import json
from pathlib import Path

rows = json.loads(Path("/app/experiments/reports/ollama/evaluation.json").read_text())
assert rows, "No workloads were evaluated"
assert all(r.get("session", {}).get("status") == "completed" for r in rows), "Incomplete run"
local = [r for r in rows if r["provider"] == "ollama"]
assert local, "No Ollama arm"
for row in local:
    usage = row["session"]["report"]["model_usage"]
    assert usage.get("provider") == "ollama" and usage.get("calls", 0) > 0, usage
    assert "error" not in usage, (row["workload_id"], usage)
print(f"Verified {len(local)} real Ollama workloads; raw reports copied to the host")
PY
(cd apps/web && node scripts/capture-evaluation.mjs)
