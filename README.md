# Autonomous PostgreSQL Query Performance Engineer

Controlled SQL and index experiments with deterministic safety gates and measured
candidate acceptance. PostgreSQL selects execution plans. This project explores
SQL formulations and physical indexes beyond a fixed query and schema.

**Execution status:** incomplete end-to-end acceptance. In the selected Python
3.12.16 environment, 83 tests pass and 8 PostgreSQL tests are skipped. Ruff,
formatting, strict Mypy, ESLint and strict TypeScript checks pass. The frontend
production build uses webpack and passes with the current Node 26 runtime.
The configured Node 22 build passed during the preceding verification. This
session cannot access the Docker socket. Supplied host output confirms all five
application image builds, successful stack startup, and 12 integration tests
passing against PostgreSQL 16. Both host Playwright tests pass and real desktop
and mobile screenshots are available. The small-dataset evaluation completed all
12 deterministic workloads with 10 validated candidates and no accepted changes.
Model evaluation, GitHub publication and CI remain pending.

## Implemented code

- Positive SELECT syntax, schema, relation and function policy independent of models.
- JSON plan extraction and contextual diagnostics for scans, joins, estimates and spills.
- Exact typed bag comparison with duplicate, NULL and ordering checks on finite snapshots.
- Repeated randomized paired trials, bootstrap intervals and explicit acceptance gates.
- Structured index experiments with storage limits and protected workload checks.
- Deterministic SQLGlot simplification and filter-index proposals.
- Optional OpenAI-compatible typed proposals and deterministic fallback.
- LangGraph workflow, persistent checkpoints, PostgreSQL jobs and cooperative cancellation.
- Versioned FastAPI endpoints and a Next.js SQL workspace with plans and evidence.
- Deterministic commerce generator and 12 workload definitions.
- Evaluation CLI, structured logs, Prometheus metrics, OpenTelemetry and CI definitions.

## Architecture

```mermaid
flowchart TD
  UI[Next.js SQL workspace] --> API[FastAPI]
  API --> Jobs[PostgreSQL durable session queue]
  Jobs --> Graph[LangGraph worker]
  Graph --> Validation[Deterministic SQL and correctness gates]
  Graph --> Provider[Deterministic or optional model proposals]
  Validation --> Benchmark[Isolated PostgreSQL benchmarks]
  Benchmark --> Policy[Statistical acceptance policy]
  Policy --> Jobs
  Graph --> Checkpoints[Persistent local checkpoints]
```

Python 3.12, Pydantic v2, SQLGlot, Psycopg 3, SQLAlchemy and Alembic serve the backend.
Next.js App Router, strict TypeScript, Tailwind, shadcn-style component primitives,
TanStack Query and Recharts serve the frontend. PostgreSQL 16 is the configured
database target. Docker Compose supplies local isolation.

## Prerequisites and setup

Conda, Docker with Compose, Node 22 and package-registry network access are required.
The following full-stack setup is provided but remains unverified in this environment.

```sh
conda activate postgres-query-optimizer
python --version
python -m pip --version
python -c 'import sys; print(sys.executable)'
cp .env.example .env
docker compose up --build -d
```

Open http://localhost:3000 and http://localhost:8000/docs. Compose runs Alembic
migrations and seeds 10,000 orders before starting the API and worker. Paid model
access is optional. Local mode defaults to deterministic proposals.

For a host frontend development session:

```sh
cd apps/web
npm ci
npm run dev
```

`apps/web/package-lock.json` records the installed npm resolution; CI and frontend
containers use `npm ci`. `requirements.lock` and `requirements-dev.lock` pin the
installed Python runtime/build and development dependency closures. Regenerate
Python snapshots with `python scripts/lock_dependencies.py` after an authorized
installation and successful `pip check`. These snapshots were generated on macOS
arm64; clean installation and Linux compatibility remain unverified. They are not
a verified reproducible release. Never install Python dependencies globally.

Install into the existing selected environment only:

```sh
python -m pip install --no-user -r requirements-dev.lock
python -m pip install --no-user --no-build-isolation --no-deps -e .
python -m pip check
```

## Dataset generation

```sh
docker compose stop worker
docker compose run --rm seed pg-optimizer seed --size medium --seed 42
docker compose start worker
```

Sizes are 10,000, 100,000 and 1,000,000 orders, each with three order items. Stable
hash fractions create skewed customer activity and product popularity. Edge schemas
include NULLs, duplicate foreign keys, missing relationships and empty tables.
Workloads include lookups, revenue aggregation, inventory, supplier analysis,
shipment delays, correlated subqueries, skewed joins and stable pagination.

## Optimization workflow

Select a workload in the workspace, choose a provider and submit the SQL. The API
creates a persistent session. The worker validates the query, inspects metadata,
measures a plan, proposes candidates, compares finite results and benchmarks valid
candidates. Rejected candidates retain failure reasons. The original SQL remains
the recommendation when no candidate satisfies the configured policy.

```sh
curl http://localhost:8000/api/v1/optimizations \
  -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT id FROM commerce.orders WHERE customer_id=731","provider":"deterministic"}'
```

The response contains a session ID. Retrieve status at
`/api/v1/optimizations/{id}` and JSON evidence at `/api/v1/optimizations/{id}/report`.
The frontend exports reports and displays hierarchical plans and trial measurements.

## Benchmark policy and results

Two warmup pairs precede ten measured randomized pairs by default. Reports include
server latency, planning time, root buffers, variance, index size and plan changes.
A paired bootstrap estimates a median speedup interval. p95 is omitted below 40
observations. Acceptance requires finite correctness validation, a default 10
percent latency reduction, lower speedup bound above one and bounded variance.
Index experiments additionally check all protected workloads.

The browser session completed a real index experiment and retained the original
query because the protected workload regression gate failed. The [small-dataset evaluation](experiments/reports/host-small/analysis.md) records
12 completed deterministic sessions, 10 validated candidates and no accepted
recommendations. Model arms were not run because no credential was configured. Statistical unit fixtures are not benchmark evidence. See
[benchmark methodology](docs/benchmarking.md) and [verification](docs/verification.md).

```sh
docker compose exec api pg-optimizer evaluate --workloads customer_lookup --output /app/experiments/reports/lookup
docker compose cp api:/app/experiments/reports/lookup experiments/reports/lookup
```

## Tests

Commands inside the dedicated activated Conda environment:

```sh
python -m unittest discover -s tests/unit -v
python -m pytest tests/unit tests/integration/test_agent.py
python -m ruff check packages tests
python -m ruff format --check packages tests
python -m mypy packages/optimizer
```

Real database integration requires running Compose services and host DSNs:

```sh
PGO_INTEGRATION=1 \
PGO_APP_DSN=postgresql+psycopg://pgo_app:local_app_only@localhost:5433/pgo_app \
PGO_READ_DSN=postgresql://pgo_reader:local_reader_only@localhost:5434/pgo_benchmark \
PGO_ADMIN_DSN=postgresql://pgo_experiment:local_experiment_only@localhost:5434/pgo_benchmark \
  python -m pytest tests/integration -v
cd apps/web
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

Playwright captured a real completed session. The [desktop capture](docs/assets/workspace-desktop.png)
and [mobile capture](docs/assets/workspace-mobile.png) show actual plans, trials
and the rejection decision. Screenshot review identified rendering defects.
Refreshed captures were inspected at desktop width 1280 and mobile width 390.
Charts are visible and the mobile document no longer expands beyond the viewport.
CI definitions require the same checks and do not require paid APIs.
CI has not run and is not claimed to pass.

## Repository layout

| Path | Contents |
|---|---|
| `packages/optimizer` | SQL policy, plans, benchmarks, providers, graph, API and worker |
| `apps/web` | Next.js workspace, plans, charts and browser tests |
| `datasets/schema.sql` | Commerce schema |
| `infrastructure` | Database roles, Docker, migrations and metrics configuration |
| `tests` | Unit, provider and real PostgreSQL integration tests |
| `experiments/reports` | Verification record and future measured evaluation outputs |
| `docs` | Architecture, safety, methodology, deployment and decisions |

## Limitations and remaining work

The system is not production-ready. Local static checks and a webpack production
build pass. HTTP safety and SQLite checkpoint recovery are tested with database
doubles; real PostgreSQL worker recovery remains unverified. Docker socket and
network access from the execution session are required to finish database,
browser and benchmark acceptance. No GitHub repository has been created. Local commits are stored through `scripts/git.sh` because this
host disallows writing `.git`.

Finite comparisons cannot prove arbitrary SQL equivalence. Unsupported functions
and syntax fail closed. Result-size limits can make correctness inconclusive.
Cancellation waits for the active statement timeout. One worker and one proposal
round are implemented. Write throughput, HypoPG, formal proofs, distributed workers,
adaptive model follow-up and aggregate AI-value evaluation remain future work.

Before a release, verify clean installation from the dependency locks, run the
remaining database and browser checks, fix runtime failures, execute measured
evaluation and capture actual screenshots. Publish with
`scripts/publish.sh` after GitHub CLI authentication and network access are available.
That script refuses a dirty worktree and verifies the pushed commit without force.
