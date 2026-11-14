# Evaluation

The CLI evaluator measures each original workload, then enqueues deterministic
and model-assisted sessions. It writes incremental JSON evidence and a Markdown
table. Without a model credential, the model arm is explicitly `not_run`.
A fallback deterministic run is not counted as evidence of model value.
Completed fallback-only sessions are counted separately. Their known model token
usage remains included, but their improvements do not enter model-arm outcome
rates. Model-generated and accepted-model candidate counts expose contribution
separately from deterministic proposals.

Reports retain baseline distributions, candidate results, equivalence failures,
acceptance decisions, environment settings, dataset manifest, model calls and token
usage. Model cost is null without a configured verified price. Database cost is
represented by server execution time and buffer operations rather than a currency
estimate.

The evaluator also writes `summary.json` with candidate validity, equivalence,
acceptance, workload improvement, experimental regression, speedup, runtime,
model usage and measured database execution totals. Unknown cost per success
remains null. Aggregate UI dashboards are not implemented. No model
value, speedup or superiority to PostgreSQL's planner is claimed.

Run the manually dispatched evaluation workflow for small, medium or large datasets.
Full evaluation is intentionally separate from push and pull request CI.
