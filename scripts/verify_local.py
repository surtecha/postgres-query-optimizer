"""Capture local checks without promoting unexecuted integration checks to success."""
import datetime as dt
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if "pg-optimizer-ai" not in sys.executable:
    raise SystemExit("Run inside the dedicated pg-optimizer-ai Conda environment")
sys.path.insert(0, str(ROOT / "packages"))
suite = unittest.defaultTestLoader.discover(str(ROOT / "tests/unit"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
compiled = subprocess.run([sys.executable, "-m", "compileall", "-q", "packages", "tests",
                           "infrastructure/migrations"], cwd=ROOT, check=False)
report = {
    "timestamp": dt.datetime.now(dt.UTC).isoformat(),
    "python": sys.version.split()[0],
    "interpreter": sys.executable,
    "unit_tests": {"executed": result.testsRun, "failures": len(result.failures),
                   "errors": len(result.errors), "skipped": len(result.skipped)},
    "python_syntax": "passed" if compiled.returncode == 0 else "failed",
    "tools": {name: shutil.which(name) is not None for name in ("docker", "gh", "psql", "node", "npm")},
    "integration": "not_run", "frontend_build": "not_run", "browser_tests": "not_run",
    "lint": "not_run", "typecheck": "not_run", "benchmarks": "not_run",
    "dependency_locks": "not_generated", "github_publication": "blocked",
    "blockers": ["Package registry and GitHub DNS resolution unavailable",
                 "Docker engine/CLI, PostgreSQL server tools and GitHub CLI absent",
                 "Full Python and frontend dependency sets could not be installed"],
}
output = ROOT / "experiments/reports/local-verification.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2)+"\n")
raise SystemExit(0 if result.wasSuccessful() and compiled.returncode == 0 else 1)
