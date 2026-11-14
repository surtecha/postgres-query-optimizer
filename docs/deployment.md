# Local execution and deployment

A Docker engine with Compose, Node 22, Conda and network access are required for a
fresh installation. Python 3.12 is the selected interpreter. `.env.example` contains
Compose service hostnames. Compose injects service DSNs directly.

```sh
conda env create -f environment.yml
conda activate postgres-query-optimizer
python --version
python -m pip --version
cp .env.example .env
docker compose up --build -d
```

Compose runs migrations and seeds the small dataset before the API and worker.
The web interface is at http://localhost:3000. OpenAPI is at
http://localhost:8000/docs. Database ports are 5433 for application metadata and
5434 for the benchmark workload.

For host Python commands, replace service hostnames with localhost and use the
published ports through command-scoped environment variables. Host data generation:

```sh
PGO_ADMIN_DSN=postgresql://pgo_experiment:local_experiment_only@localhost:5434/pgo_benchmark \
  python -m optimizer.cli seed --size medium --seed 42
```

Stop the worker before regenerating data. The generator refuses regeneration while
an active experiment holds the advisory lock. Starting the worker again resumes
queued jobs, subject to session deadlines.

```sh
docker compose stop worker
docker compose run --rm seed pg-optimizer seed --size medium --seed 42
docker compose start worker
docker compose exec api alembic upgrade head
docker compose down
```

`docker compose down --volumes` removes only this Compose project's disposable
volumes. It destroys session history, checkpoints and generated benchmark data.

Optional telemetry:

```sh
PGO_OTLP_ENDPOINT=http://jaeger:4318/v1/traces docker compose --profile observability up -d
```

Prometheus is at http://localhost:9090. Jaeger is at http://localhost:16686.
Worker metrics use port 9101. API metrics use `/metrics`. An authenticated API
requires a matching Prometheus bearer configuration.

The single worker and SQLite checkpoint volume are local deployment choices.
Cloud deployment needs persistent volumes, database backups, TLS and an authenticated
reverse proxy. Horizontal worker scaling requires a different checkpoint backend
and workload-level isolation. No cloud deployment was performed.
