"""Capture local checks without promoting unexecuted integration checks to success."""
import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if Path(sys.prefix).name != "postgres-query-optimizer":
    raise SystemExit("Run inside the dedicated postgres-query-optimizer Conda environment")
sys.path.insert(0, str(ROOT / "packages"))
loader = unittest.TestLoader()
suite = loader.discover(str(ROOT / "tests/unit"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
compiled = subprocess.run([sys.executable, "-m", "compileall", "-q", "packages", "tests",
                           "infrastructure/migrations"], cwd=ROOT, check=False)
report = {
    "timestamp": dt.datetime.now(dt.UTC).isoformat(),
    "python": sys.version.split()[0],
    "interpreter": sys.executable,
    "unit_tests": {"runner": "unittest; pytest-style functions are not included",
                   "status": "passed" if result.wasSuccessful() else "failed",
                   "executed": result.testsRun - len(loader.errors),
                   "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
                   "failures": len(result.failures),
                   "errors": len(result.errors), "skipped": len(result.skipped),
                   "discovery_errors": len(loader.errors)},
    "python_syntax": "passed" if compiled.returncode == 0 else "failed",
    "tools": {name: shutil.which(name) is not None for name in ("docker", "gh", "psql", "node", "npm")},
    "integration": "not_run", "frontend_build": "not_run", "browser_tests": "not_run",
    "lint": "not_run", "typecheck": "not_run", "benchmarks": "not_run",
    "missing_check_modules": [name for name in ("sqlglot", "pytest", "ruff", "mypy")
                              if importlib.util.find_spec(name) is None],
    "network": "not_checked_by_this_script",
    "github_publication": "not_checked_by_this_script",
}
output = ROOT / "experiments/reports/local-verification.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2)+"\n")
raise SystemExit(0 if result.wasSuccessful() and compiled.returncode == 0 else 1)
