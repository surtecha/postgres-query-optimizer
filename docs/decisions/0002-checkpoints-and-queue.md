# Durable queue and local checkpoints

Status: accepted for local deployment

PostgreSQL holds sessions and serialized reports. Row locks and a worker-wide
advisory lock avoid duplicate active workers. LangGraph records typed intermediate
state in SQLite on a persistent volume. This provides recovery without Redis or a
second application queue service.

SQLite constrains execution to one worker on one host. A distributed deployment
requires PostgreSQL-backed LangGraph checkpoints and stronger experiment isolation.
Checkpoint replay can repeat a benchmark stage. Stable index names and cleanup
make replay recoverable but do not make benchmark observations exactly once.
