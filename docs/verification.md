# Execution evidence

Local verification was performed on 14 November 2026 with Python 3.12.15 inside a
workspace-local Conda environment named `pg-optimizer-ai`. Cached Python artifacts
were used because network DNS and default Conda directories were unavailable.
One cached Tk dependency declared an older zlib constraint. The interpreter and
SQLGlot checks ran, but the environment is not a resolved release environment.
The committed environment specification requires a fresh normal Conda resolution.

Subsequent development targets the supplied `postgres-query-optimizer` Conda
environment with Python 3.12.16. Its interpreter was verified. Dependency
installation remains blocked by read-only site-packages and unavailable registry
DNS. The unit results below belong to the earlier environment and have not been
fully reproduced in the replacement environment. The current partial results below
supersede the historical table for the selected environment.

## Historical results: previous environment

| Check | Actual result |
|---|---|
| Unit tests | 47 executed, 47 passed, 0 failed, 0 skipped |
| Python syntax compilation | Passed for packages, tests and migrations |
| SQL parser | SQLGlot 30.18.0, all 12 workloads accepted |
| Full Python dependencies | Incomplete, installation blocked by DNS |
| Ruff and Mypy | Not installed, not run |
| Docker and PostgreSQL startup | Not run, required tools absent |
| PostgreSQL integration tests | Written, not run |
| Frontend dependency installation | Failed with ENOTFOUND for npm registry |
| Frontend lint, types and build | Not run |
| Playwright and screenshots | Not run, no screenshots generated |
| Evaluation and speedups | Not run, no measured results |
| GitHub publication | Blocked, GitHub CLI absent and GitHub DNS unavailable |
| GitHub Actions | Configured, not run |

`experiments/reports/local-verification.json` records machine-readable results.
`python scripts/verify_local.py` regenerates the local unit and syntax evidence.
Unit test timing and synthetic statistical fixtures are not PostgreSQL benchmarks.

## Outstanding acceptance

Network access, Docker and GitHub CLI are necessary to complete the task. Full
runtime dependencies must be resolved and locked. Python lint and types, frontend
lint and build, PostgreSQL tests, worker recovery tests and real browser workflows
must run. Runtime or static-check failures must be fixed before publication as a
verified release. Real evaluation reports and application screenshots remain absent.

The current implementation has not met the definition of done. Documentation and
local commits preserve the implemented work without claiming deployment success.


## Resumed verification: 14 November 2026

Starting state: `a062928`, 13 commits, clean worktree, no configured remote.
Selected interpreter: `/Users/surtecha/Tools/miniconda/envs/postgres-query-optimizer/bin/python`,
Python 3.12.16. No replacement environment or global/user Python installation was used.

| Check | Observed result |
|---|---|
| Environment write probe | `PermissionError: Operation not permitted` in selected site-packages |
| Conda channels | DNS failed for repo.anaconda.com and conda.anaconda.org |
| Python/npm registries | DNS failed for pypi.org and registry.npmjs.org |
| Container registries | DNS failed for registry-1.docker.io and ghcr.io |
| GitHub API | DNS failed for api.github.com |
| Docker Engine/Compose | Docker command absent; engine and Compose unavailable for verification |
| GitHub CLI/authentication | gh command absent; authentication unverified |
| PostgreSQL CLI | psql absent from PATH |
| Host frontend runtime | Node v26.13.0, npm 11.20.0; configured Node 22 target not verified |
| Python install | Selected interpreter with `pip install --no-user -e '.[dev]'` failed resolving build dependencies over DNS |
| npm lock generation | `npm install --package-lock-only --ignore-scripts` failed with ENOTFOUND |
| Current unit suite | 35 actual tests passed; 1 discovery error for missing SQLGlot; full suite failed |
| Syntax compilation | packages, tests and migrations passed |
| Ruff check/format, Mypy, Pytest | Commands attempted; modules missing, checks did not run |
| ESLint, TypeScript, frontend build, Playwright | Commands attempted; executables missing, checks did not run |
| PostgreSQL integration/security and worker recovery | Not run |
| All 12 workload evaluations | Not run; no measured distributions or acceptance decisions |
| Model-assisted evaluation | Not run; credential availability not checked because stack unavailable |
| Screenshots, publication and Actions | Not produced or run |

The result comparator previously collapsed nested object, array and tuple types
into identical keys. Four new regression cases failed before the fix and passed
after type-tagging container keys; all 14 result-comparison tests passed.
Plan and statistics tests were separated from SQL-parser imports, preserving the
original test classes exactly. Missing SQLGlot still fails discovery; no checks
were skipped or weakened. The verification script now distinguishes actual tests
from discovery failures and does not assert unprobed network status.

## Required manual execution-access changes

The session policy disables sandbox approval requests. An in-session approval
cannot grant the missing filesystem or network access.

1. Add `/Users/surtecha/Tools/miniconda/envs/postgres-query-optimizer` to the
   execution host's permitted writable roots. Grant the entire environment,
   including `bin`, `lib/python3.12/site-packages`, and package metadata; changing
   Unix permissions alone does not remove the sandbox restriction.
2. Enable DNS resolution and outbound HTTPS in the execution host for Conda,
   PyPI (including files.pythonhosted.org), npm, Docker Hub authentication/image
   delivery, ghcr.io, and GitHub API/Git endpoints. Registry redirects and artifact
   delivery endpoints must also be reachable. Git transport must be permitted.
3. Install/start Docker Desktop with Compose v2 on the host and expose its CLI
   and engine socket to this workspace session. Install GitHub CLI and authenticate
   through `gh auth login` with repository creation and push access. Credentials
   must remain in the host credential store.
4. Provide the configured Node 22 runtime in PATH. Retain the existing Conda
   environment. Resume installation with the exact selected interpreter and
   `-m pip install --no-user -e '.[dev]'`; no global or user fallback is permitted.

Dependency locks, full static checks, stack execution, integration/security tests,
recovery/cancellation tests, browser flows, screenshots, 12-workload measurements,
publication, CI and remote-commit verification remain incomplete. The partial
stdlib test results provide no PostgreSQL performance or production-readiness evidence.


## Latest verification after host setup: 14 November 2026

This section supersedes earlier dependency and local-check statuses. Docker Desktop
and GitHub authentication succeeded in the supplied host Terminal output. The
session independently finds Docker and GitHub CLI, but Docker socket access is
denied and PyPI/npm/GitHub DNS still fails. The Conda environment remains read-only
inside the session; host-installed packages are available for execution.

| Check | Actual result |
|---|---|
| Interpreter | Selected Conda environment, Python 3.12.16 |
| Dependency consistency | `python -m pip check`: no broken requirements |
| Ruff lint and format | Passed for packages and tests |
| Strict Mypy | Passed, 21 source files; strictness retained |
| Full Pytest suite | 68 passed, 8 PostgreSQL tests skipped, 1 dependency deprecation warning |
| Unittest subset | 52 passed; pytest-style functions are outside this runner |
| Python syntax | Passed for packages, tests and migrations |
| ESLint | Passed |
| Strict TypeScript | Passed; route types generated before tsc |
| Frontend production build | Passed with `npm run build -- --webpack`, Node 22.23.5 |
| Default frontend build | Turbopack blocked by denied local port binding; not verified |
| Compose configuration | `docker compose config --quiet` passed |
| Docker Engine access | Host running; session denied at `/Users/surtecha/.docker/run/docker.sock` |
| Browser installation | Playwright lists Chromium, headless shell and ffmpeg installations |
| Browser tests/screenshots | Not run or produced; real services inaccessible |
| Python locks | 72 runtime/build and 103 development distributions pinned from installed metadata |
| npm lock | Generated by successful host installation; root dependencies match manifest |
| Clean lock installation/container builds | Not verified |
| PostgreSQL integration, roles, migrations, seed and worker | Not executed in this session |
| Benchmarks | No original/deterministic/model measurements; all 12 workloads incomplete |
| Model credential | Not configured in session Settings; model arm not run |
| GitHub publication/Actions | No remote configured; neither executed |

`experiments/reports/resumed-verification.json` records these observations.
The Python lock generator evaluates installed dependency metadata, optional extras,
and environment markers after pip check. Linux marker evaluation found no missing
installed distribution metadata, but this does not validate Linux wheels, installation,
or execution. The snapshots do not contain artifact hashes. CI and containers now
consume the locks; successful remote execution remains required.

Changes were committed at separate milestones: Ruff formatting, strict typing,
frontend lint fixes, dependency locks, HTTP/checkpoint tests, and execution-cost
safety. `EXPLAIN ANALYZE` now performs an estimated-cost preflight even when called
directly. Tests verify over-budget queries never reach analyzed execution using
recorded response doubles. HTTP tests verify unsafe SQL and oversized chunked bodies
are not enqueued, remote authentication, workload matching, missing-session handling,
and error redaction. SQLite tests reopen a real checkpoint file after a failed
stage and verify resume/cancellation; PostgreSQL queue and process interruption
behavior remains unverified.

The remaining manual access change is to permit the execution session to access
the Docker Engine socket and outbound DNS/HTTPS, with selected-environment writes
when installations are needed. Host installation and host authentication do not
change the existing session sandbox. No Docker socket proxy, permission workaround,
or alternative environment was introduced. After access is available, remaining
acceptance includes clean installs, default/container builds, PostgreSQL/security
and process-recovery tests, browser workflows and screenshots, all 12 measured
workloads, public publication, Actions, and final remote-commit verification.

## Current continuation verification: 14 November 2026

The selected environment supplies Python 3.12.16 and the installed dependencies.
Dependency consistency, Ruff lint and formatting, strict Mypy, ESLint and strict
TypeScript checks pass. The full Pytest suite now reports 83 passed, 8 explicitly
skipped PostgreSQL integration tests and one dependency deprecation warning.
Compose configuration validation passes.

Four scope-rebinding regressions verify that nested CTE names cannot prevent outer
base relations from being switched to differential datasets. Eight provider tests
cover empty choices, empty content, invalid schemas, truncated output, timeouts and
successful structured responses. Six provider cases failed before the correction.
Known token usage now survives schema errors. Three evaluation cases verify that
fallback-only results are excluded from model-arm outcome rates while known usage
remains accounted for.

The standard `npm run build` command now selects webpack and passes with Node
26.13.0. The earlier webpack build on Node 22 remains recorded above. Turbopack
still fails because the execution session denies its internal port binding.
Webpack requires no such internal server for this build.

Docker CLI 29.9.3 and Compose v5.7.0 are installed. The configured Docker Desktop
socket is unavailable from this session with a no-such-file error. Launching
Docker through the host application launcher also reports that the application
is unavailable in this session. No socket proxy or alternate endpoint was used.
PyPI and GitHub API DNS probes still fail. GitHub authentication therefore cannot
be validated, and no remote is configured. Host authentication is not assumed
invalid solely because the session cannot resolve the API hostname.

PostgreSQL execution, container builds, real browser tests, screenshots, measured
workloads, publication and Actions remain blocked and are not claimed complete.
`experiments/reports/continuation-verification.json` records the current results.
