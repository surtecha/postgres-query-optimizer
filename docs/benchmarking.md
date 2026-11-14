# Benchmark methodology

The generator provides 10,000, 100,000 and 1,000,000 orders, with three order items
per order. Stable MD5-derived fractions produce skewed customers and products.
A fixed timestamp origin avoids date-dependent samples. The manifest records seed
and order count. The generator refuses a database or role outside the local
benchmark contract.

The benchmark uses two warmup pairs followed by configurable measured pairs.
Each pair randomizes baseline and candidate order with seed 42. An index candidate
creates and removes its experimental index between variants. DDL time is excluded
from server execution latency. Repeated index construction increases total
optimization time. It can also warm buffers, so results must be read as local
warm-cache experiments rather than cold-cache capacity measurements.

EXPLAIN ANALYZE JSON supplies server execution time, planning time and root buffer
counts. Parent buffer counts and execution times are inclusive. Diagnostics do not
sum them across the tree. Client wall duration is recorded separately. Identical
query parameters, PostgreSQL settings and deterministic datasets are used.

## Acceptance

Every candidate requires positive SQL validation and exact finite result checks.
Default policy requires a 10 percent median latency reduction, a lower 95 percent
paired bootstrap speedup bound above one, coefficient of variation at most 0.35,
and index size at most 64 MiB. The bootstrap uses 2,000 deterministic resamples.

Index experiments also measure all 12 protected queries with five randomized pairs.
Every protected query must have a lower speedup bound of at least 0.9. This is a
conservative noisy regression screen, not a multiple-comparison significance test.
Write amplification is disclosed but write throughput is not measured.

p95 is omitted below 40 observations. Small sample bootstrap intervals are reported
with a warning. A bootstrap cannot remove cache effects, autocorrelation, noisy
neighbors or configuration bias. There are no verified speedups in this checkout
because PostgreSQL could not be started in the execution environment.

## Reproduction

```sh
docker compose up --build -d
docker compose exec api pg-optimizer evaluate --workloads customer_lookup --output /app/experiments/reports/lookup
docker compose cp api:/app/experiments/reports/lookup experiments/reports/lookup
```

These stack commands have not been executed successfully in the current environment.
