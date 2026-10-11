"""File-based experiment control from the dev container; worker runs in PC1 WSL.

Uses the existing workspace bind mount, no Docker socket or private SSH keys
are exposed to the container. Requests are trusted local project instructions.
Only job operations and source synchronization are accepted, not shell strings.
"""

import argparse
import fcntl
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / ".runtime/control"


def command(request):
    backend, action = request["backend"], request["action"]
    if backend not in {"pc1", "h100"}:
        raise ValueError("Unknown backend")
    args = ["bash", "scripts/experiment.sh", backend]
    if action == "status":
        return args + ["status"]
    if action == "sync" and backend == "h100":
        return ["bash", "scripts/sync_h100.sh"]
    value = request.get("value", "")
    if action in {"logs", "cancel"} and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        return args + [action, value]
    if action == "submit":
        path = (PROJECT / value).resolve()
        if not path.is_relative_to(PROJECT / "configs/jobs") or not path.is_file():
            raise ValueError("Only existing configs/jobs/*.json specs can be submitted")
        spec = json.loads(path.read_text())
        if spec["backend"] not in {backend, "cpu"}:
            raise ValueError("Backend/spec mismatch")
        return args + ["submit", str(path.relative_to(PROJECT))]
    raise ValueError("Unsupported control request")


def atomic(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data) + "\n")
    os.replace(temp, path)


def serve():
    if not Path("/mnt/c/Windows/System32/OpenSSH/ssh.exe").exists():
        raise SystemExit("Control worker must run in PC1 WSL, outside the container")
    with (ROOT / "worker.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Interrupted requests are not retried blindly: remote submit may have succeeded.
        for old in (ROOT / "processing").glob("*.json"):
            atomic(ROOT / "responses" / old.name, {
                "returncode": 1,
                "stderr": "Worker interrupted. Inspect target status before retry.",
                "stdout": "", "outcome_unknown": True,
            })
            old.rename(ROOT / "archive" / old.name)
        while True:
            atomic(ROOT / "heartbeat.json", {"time": time.time(), "pid": os.getpid()})
            for path in sorted((ROOT / "requests").glob("*.json")):
                pending = ROOT / "processing" / path.name
                path.rename(pending)
                try:
                    result = subprocess.run(command(json.loads(pending.read_text())),
                                            cwd=PROJECT, stdin=subprocess.DEVNULL,
                                            capture_output=True, text=True, timeout=120)
                    response = {"returncode": result.returncode,
                                "stdout": result.stdout[-64000:], "stderr": result.stderr[-16000:]}
                except Exception as exc:
                    response = {"returncode": 1, "stdout": "", "stderr": str(exc),
                                "outcome_unknown": isinstance(exc, subprocess.TimeoutExpired)}
                atomic(ROOT / "responses" / path.name, response)
                pending.rename(ROOT / "archive" / path.name)
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=["pc1", "h100", "worker"])
    parser.add_argument("action", choices=["status", "logs", "cancel", "submit", "sync"], nargs="?")
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    for name in ["requests", "processing", "responses", "archive"]:
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    if args.backend == "worker":
        serve()
        return
    req = {"backend": args.backend, "action": args.action, "value": args.value}
    command(req)  # Validate before enqueuing.
    heartbeat = ROOT / "heartbeat.json"
    if not heartbeat.exists() or time.time() - json.loads(heartbeat.read_text())["time"] > 150:
        raise SystemExit("PC1 control worker is offline. Run scripts/start_control.sh in PC1 WSL.")
    request_id = uuid.uuid4().hex
    path = ROOT / "requests" / f"{request_id}.json"
    atomic(path, req)
    response = ROOT / "responses" / path.name
    deadline = time.monotonic() + 135
    while time.monotonic() < deadline:
        if response.exists():
            data = json.loads(response.read_text())
            print(json.dumps(data, indent=2))
            raise SystemExit(0 if data["returncode"] == 0 else 1)
        time.sleep(1)
    raise SystemExit(
        f"Outcome unknown; inspect .runtime/control/responses/{path.name}. Do not resubmit."
    )


if __name__ == "__main__":
    main()
