from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "container_smoke.sh"


def executable(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + contents)
    path.chmod(0o755)


@pytest.mark.parametrize("failure", ["start", "request"])
def test_failed_smoke_preserves_diagnostics_and_exit_code(tmp_path: Path, failure: str) -> None:
    executable(tmp_path / ".venv/bin/python", 'echo "fake MCP log"\n')
    commands = tmp_path / "commands"
    executable(
        commands / "docker",
        """echo "$1" >> "$SMOKE_TEST_CALLS"
case "$1" in
  run) if [[ "$SMOKE_TEST_FAILURE" == start ]]; then exit 23; fi ;;
  logs) echo "agent diagnostic" ;;
  inspect) echo '{"State":{"Status":"exited"}}' ;;
esac
""",
    )
    executable(
        commands / "curl",
        """case "$*" in
  *reserve-recommended-seat*)
    while [[ $# -gt 0 ]]; do
      if [[ "$1" == --output ]]; then echo '{"error":"smoke failure"}' > "$2"; break; fi
      shift
    done
    exit 22 ;;
  *) echo 200 ;;
esac
""",
    )
    output = tmp_path / "diagnostics"
    calls = tmp_path / "calls"
    result = subprocess.run(
        ["bash", str(SCRIPT), "agent:test", str(output)],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{commands}:{os.environ['PATH']}",
            "SMOKE_TEST_FAILURE": failure,
            "SMOKE_TEST_CALLS": str(calls),
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    expected = 23 if failure == "start" else 22
    assert result.returncode == expected
    assert (output / "exit-status.txt").read_text().strip() == str(expected)
    assert "agent diagnostic" in (output / "agent.log").read_text()
    assert "exited" in (output / "container.json").read_text()
    assert (output / "recommendation.log").is_file()
    assert (output / "reservation.log").is_file()
    assert "rm" in calls.read_text().splitlines()
    assert "Smoke diagnostics retained:" in result.stdout
    if failure == "request":
        assert '"error":"smoke failure"' in (output / "response.json").read_text()
