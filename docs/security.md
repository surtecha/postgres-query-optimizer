# Security boundaries

The initial target is a controlled local commerce database. Unrestricted production
analysis is unsupported. Compose binds services to loopback. Development passwords
are public local defaults and must be replaced before any remote deployment.

SQL acceptance uses a positive AST node policy, relation allowlist, function
allowlist and exactly one SELECT expression. Schema-qualified functions and
unknown syntax fail closed. Reader sessions enforce repeatable-read, read-only
transactions, statement and lock timeouts. Result comparison uses server cursors
with row and byte limits. EXPLAIN estimated cost gates precede measured execution.

A hostile query can still consume its bounded database budget. The Compose
benchmark service limits CPU, memory and connections. PostgreSQL is the final
read-only enforcement boundary. The reader cannot create schema objects. The
experiment role owns benchmark objects and is never used for submitted SELECTs.

Index proposals contain identifiers and optional typed literal predicates. Psycopg
identifier and literal composition produces DDL. A reserved experimental index
prefix limits cleanup. The experiment lock excludes other cooperating workers and
the generator. It does not prevent writes by an unrelated administrator. Benchmarks
assume no external writers, and no external database connection should be supplied.

Remote API mode requires a token of at least 32 characters. The frontend forwards
an operator-entered bearer token without embedding a server credential in the page.
Token state remains in memory. The API has a persistent pending-job quota. This is
not a per-client rate limiter. Add TLS, identity integration, network isolation,
secret management and deployment-specific resource policies before remote use.

Request body limits include chunked requests. User errors return 422. Infrastructure
errors return safe categories. Logs contain stage metadata, not connection strings.
Reports contain submitted SQL and database metadata and should be access controlled.

Browser POST origins are compared with the incoming HTTP Host and request scheme.
The internal Docker bind address is not a browser origin. Cross-origin hosts, ports,
schemes, malformed origins and opaque origins remain rejected. Forwarded-host
headers do not authorize an origin. A reverse proxy must preserve the intended
Host and scheme. Requests without Origin still require configured bearer access.

Dependency and security CI jobs are configured but have not run. Dependency locks
are not available because package registries could not be reached. No security
review or production-readiness certification is claimed.
