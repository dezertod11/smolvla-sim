"""Exercise real supervision on tiny CPU subprocesses, without model/GPU use."""

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/jobs.py"


def call(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          capture_output=True, text=True, timeout=30)


def start(tmp_path, code, seconds=10):
    root = tmp_path / "runs"
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"id": "test", "backend": "cpu", "kind": "check",
                                "timeout_seconds": seconds,
                                "command": ["{python}", "-c", code]}))
    result = call(root, "submit", str(spec))
    assert result.returncode == 0, result.stderr
    return root, spec


def finish(root):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        state = json.loads((root / "test/state.json").read_text())
        if state["status"] in {"succeeded", "failed", "timed_out", "cancelled"}:
            return state
        time.sleep(0.1)
    raise AssertionError("Supervisor did not finish")


def test_success_and_duplicate(tmp_path):
    root, spec = start(tmp_path, "print('success')")
    assert finish(root)["status"] == "succeeded"
    assert call(root, "submit", str(spec)).returncode != 0
    assert "success" in (root / "test/console.log").read_text()
    assert (root / "test/source_sha256.json").is_file()


def test_nonzero_exit(tmp_path):
    root, _ = start(tmp_path, "raise SystemExit(7)")
    state = finish(root)
    assert state["status"] == "failed"
    assert state["exit_code"] == 7


def test_timeout(tmp_path):
    root, _ = start(tmp_path, "import time; time.sleep(60)", seconds=1)
    assert finish(root)["status"] == "timed_out"


def test_cancel(tmp_path):
    root, _ = start(tmp_path, "import time; time.sleep(60)")
    assert call(root, "cancel", "test").returncode == 0
    assert finish(root)["status"] == "cancelled"
