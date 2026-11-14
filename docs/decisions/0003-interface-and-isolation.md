# Local experiment product boundary

Status: accepted

FastAPI provides typed request contracts and a synchronous database access boundary
inside its thread pool. Next.js provides the web workspace and same-origin API
forwarding. TanStack Query polls durable session status. The UI uses real API data,
expandable plan nodes and repeated latency charts.

Application metadata and benchmark data use separate PostgreSQL services. Index
experiments require a named benchmark database and role. Isolation permits physical
design experiments without changing an external database. Runtime verification of
the complete stack remains blocked in the current environment.
