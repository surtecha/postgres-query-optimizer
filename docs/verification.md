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
