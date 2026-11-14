"""Run local acceptance checks and retain results without claiming stack execution."""

import datetime as dt
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if Path(sys.prefix).name != "postgres-query-optimizer":
        raise SystemExit("Run inside the dedicated postgres-query-optimizer Conda environment")
    checks = {}
    with tempfile.TemporaryDirectory(prefix="pgo-verification-") as temporary:
        junit = Path(temporary) / "tests.xml"
        commands = {
            "dependencies": [sys.executable, "-m", "pip", "check"],
            "python_tests": [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit",
                "tests/integration/test_agent.py",
                "-q",
                f"--junitxml={junit}",
            ],
            "python_lint": [sys.executable, "-m", "ruff", "check", "packages", "tests", "scripts"],
            "python_format": [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "packages",
                "tests",
                "scripts",
            ],
            "python_types": [sys.executable, "-m", "mypy", "packages/optimizer"],
            "web_lint": ["npm", "run", "lint"],
            "web_types": ["npm", "run", "typecheck"],
            "web_unit": ["npm", "run", "test:unit"],
            "web_build": ["npm", "run", "build"],
            "compose_config": ["docker", "compose", "config", "--quiet"],
        }
        for name, command in commands.items():
            print(f"Checking {name}", flush=True)
            try:
                result = subprocess.run(
                    command,
                    cwd=ROOT / "apps/web" if name.startswith("web_") else ROOT,
                    check=False,
                    timeout=600,
                )
                checks[name] = {"status": "passed" if result.returncode == 0 else "failed"}
            except (OSError, subprocess.TimeoutExpired) as exc:
                checks[name] = {"status": "failed", "category": type(exc).__name__}
        if junit.exists():
            suites = list(ET.parse(junit).getroot().iter("testsuite"))
            counts = {
                name: sum(int(suite.attrib.get(name, 0)) for suite in suites)
                for name in ("tests", "failures", "errors", "skipped")
            }
            checks["python_tests"].update(counts)
    report = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "checks": checks,
        "integration": "not_run",
        "worker_process_recovery": "not_run",
        "browser_tests": "not_run",
        "benchmarks": "not_run",
        "github_publication": "not_checked_by_this_script",
    }
    output = ROOT / "experiments/reports/local-verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return int(any(check["status"] != "passed" for check in checks.values()))


if __name__ == "__main__":
    raise SystemExit(main())
