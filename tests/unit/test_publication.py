"""Exercise publication decisions without accessing GitHub or modifying Git metadata."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("scenario", "success", "pushed"),
    [
        ("existing", True, True),
        ("dirty", False, False),
        ("branch", False, False),
        ("mismatch", False, True),
    ],
)
def test_existing_remote_publication(tmp_path, scenario, success, pushed):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (tmp_path / ".git-store").mkdir()
    for name in ("git.sh", "publish.sh"):
        shutil.copy2(ROOT / "scripts" / name, scripts / name)
    binary = tmp_path / "bin"
    binary.mkdir()
    stub = (
        f"#!{sys.executable}\n"
        + """
import json
import os
import sys
from pathlib import Path

command = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["COMMAND_LOG"], "a") as log:
    log.write(json.dumps([command, *args]) + "\\n")
scenario = os.environ["SCENARIO"]
if command == "gh":
    if args != ["auth", "status"]:
        raise SystemExit("Unexpected GitHub mutation")
elif args[:2] == ["status", "--porcelain"]:
    if scenario == "dirty":
        print(" M README.md")
elif args[:2] == ["branch", "--show-current"]:
    print("feature" if scenario == "branch" else "main")
elif args[:2] == ["remote", "get-url"]:
    print("https://github.com/example/project.git")
elif args[0] == "rev-parse":
    print("a" * 40)
elif args[0] == "ls-remote":
    print(("b" if scenario == "mismatch" else "a") * 40 + "\\trefs/heads/main")
elif args != ["push", "--set-upstream", "origin", "main"]:
    raise SystemExit("Unexpected Git command: " + repr(args))
"""
    )
    for name in ("git", "gh"):
        path = binary / name
        path.write_text(stub)
        path.chmod(0o755)
    log = tmp_path / "commands.jsonl"
    result = subprocess.run(
        ["sh", str(scripts / "publish.sh")],
        env={
            **os.environ,
            "PATH": str(binary) + os.pathsep + os.environ["PATH"],
            "SCENARIO": scenario,
            "COMMAND_LOG": str(log),
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (result.returncode == 0) == success, result.stderr
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    assert (["git", "push", "--set-upstream", "origin", "main"] in commands) == pushed
    assert [command for command in commands if command[0] == "gh"] == [["gh", "auth", "status"]]
