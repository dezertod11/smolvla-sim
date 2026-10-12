"""Detached Linux experiment supervisor. No scheduler or LLM is hidden here.

GPU jobs require an explicit, separately stored budget approval. Commands are
trusted project code, not a security sandbox. Bounded concurrency, unique run IDs,
immutable source copies, bounded runtime, cancellation without PID guessing.
"""

import argparse
import contextlib
import csv
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from h100_run import ALLOWED_ROOT, select_gpu

PROJECT = Path(__file__).resolve().parents[1]
FINAL = {"succeeded", "failed", "cancelled", "timed_out", "launch_failed"}


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(tmp, path)


@contextlib.contextmanager
def lock(path, blocking=True):
    with Path(path).open("a") as handle:
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        fcntl.flock(handle, flags)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def validate(spec):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", spec["id"]):
        raise ValueError("Invalid run ID")
    if spec["backend"] not in {"pc1", "h100", "cpu"}:
        raise ValueError("Unknown backend")
    if spec["kind"] not in {"train", "eval", "check", "prepare"}:
        raise ValueError("Unknown kind")
    if not isinstance(spec["timeout_seconds"], int) or spec["timeout_seconds"] < 1:
        raise ValueError("Positive timeout required")
    if not spec["command"] or not all(isinstance(x, str) for x in spec["command"]):
        raise ValueError("command must be a nonempty argv list, never a shell string")
    if spec["kind"] == "check" and spec["timeout_seconds"] > 120:
        raise ValueError("CPU checks are limited to 120 seconds")
    if spec["kind"] == "prepare" and spec["timeout_seconds"] > 1800:
        raise ValueError("CPU preparation is limited to 1800 seconds")
    if spec["backend"] == "cpu" and spec["kind"] != "check":
        raise ValueError("CPU backend is for infrastructure checks only")


def authorize(spec, policy, records):
    if spec["kind"] in {"check", "prepare"}:
        return
    if policy.get("approved") is not True or not policy.get("approval_note"):
        raise ValueError("Training/evaluation budget has not been approved by the user")
    bucket = policy["limits"][spec["backend"]][spec["kind"]]
    prior = [r for r in records if r["spec"]["kind"] == spec["kind"]
             and r["spec"]["backend"] == spec["backend"]]
    # Active work reserves its full timeout. Completed work is charged by measured
    # wall time, which preserves the approved GPU-hour ceiling without letting a
    # fast pre-flight failure consume hours that were never used.
    reserved = sum(
        r.get("elapsed_seconds", r["spec"]["timeout_seconds"])
        if r["status"] in FINAL else r["spec"]["timeout_seconds"]
        for r in prior
    )
    if len(prior) >= bucket["max_runs"]:
        raise ValueError("Run-count budget exhausted")
    if reserved + spec["timeout_seconds"] > bucket["max_seconds"]:
        raise ValueError("Time budget exhausted")
    if spec["timeout_seconds"] > bucket["max_run_seconds"]:
        raise ValueError("Per-run time budget exceeded")


def locations(backend):
    if backend == "h100":
        if not PROJECT.is_relative_to(ALLOWED_ROOT):
            raise ValueError("H100 commands must run within the permitted project")
        data = PROJECT / ".runtime"
        python = PROJECT / ".venv/bin/python"
    elif backend == "pc1":
        if not Path("/opt/venv/bin/python").exists() or not Path("/data").is_dir():
            raise ValueError("PC1 jobs run inside the prepared dev container")
        data, python = Path("/data"), Path("/opt/venv/bin/python")
    else:
        data, python = PROJECT / ".runtime", Path(sys.executable)
    return data, python


def snapshot(destination):
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=PROJECT,
    ).decode().split("\0")
    hashes = {}
    for name in sorted(set(names) - {""}):
        source = PROJECT / name
        if source.is_symlink():
            raise ValueError(f"Source symlink requires review: {name}")
        if not source.is_file():
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    return hashes


def records(root):
    return [read(p) for p in sorted(root.glob("*/state.json"))]


def submit(root, spec, budget):
    validate(spec)
    locations(spec["backend"])
    root.mkdir(parents=True, exist_ok=True)
    with lock(root / ".submit.lock"):
        existing = records(root)
        if any(r["spec"]["id"] == spec["id"] for r in existing):
            raise ValueError("Run ID already exists; inspect it instead of resubmitting")
        active = [r for r in existing if r["status"] not in FINAL]
        concurrency = 3 if spec["backend"] == "h100" else 1
        if len(active) >= concurrency or any(
            time.time() - r.get("heartbeat_at", r["created_at"]) > 60 for r in active
        ):
            raise ValueError("An existing job is active or needs recovery; inspect status")
        policy = read(budget) if budget.exists() else {}
        authorize(spec, policy, existing)
        run = root / spec["id"]
        run.mkdir()  # Also catches abandoned/incomplete submission directories.
        state = {"spec": spec, "status": "preparing", "created_at": time.time()}
        write(run / "state.json", state)
        try:
            hashes = snapshot(run / "source")
            write(run / "source_sha256.json", hashes)
            write(run / "budget.json", policy)
            state["git_commit"] = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True
            ).strip()
            state["status"] = "queued"
            write(run / "state.json", state)
            with (run / "supervisor.log").open("ab") as log:
                p = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), "--root", str(root),
                     "worker", spec["id"]], stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                    close_fds=True,
                )
            # Worker owns state from this point; no racing parent update.
            write(run / "launcher.json", {"supervisor_pid": p.pid})
        except Exception as exc:
            state.update(status="launch_failed", error=str(exc))
            write(run / "state.json", state)
            raise
    return read(run / "state.json")


def stop_child(child):
    # This child is still owned/unreaped by this supervisor. Never kill a saved PID.
    if child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()


def worker(root, run_id):
    run = root / run_id
    state = read(run / "state.json")
    spec = state["spec"]
    child = None
    interrupted = False

    def interrupt(_signum, _frame):
        nonlocal interrupted
        interrupted = True

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    execution_root = run if spec["backend"] == "h100" else root
    execution_lock = execution_root / ".execution.lock"
    with lock(execution_lock, blocking=False), contextlib.ExitStack() as leases:
        try:
            data, python = locations(spec["backend"])
            if spec["kind"] != "check" and shutil.disk_usage(data).free < 20 * 1024**3:
                raise RuntimeError("Less than 20 GiB free; refusing a GPU job")
            env = os.environ.copy()
            env.update(PYTHONUNBUFFERED="1", PYTHONPATH=str(run / "source/src"),
                       ROBOTICS_DATA_DIR=str(data), WANDB_MODE="offline",
                       ACCELERATE_MIXED_PRECISION="bf16", MUJOCO_GL="egl")
            if spec["backend"] == "h100":
                for key, subdir in {"HOME": "home", "HF_HOME": "huggingface",
                                    "XDG_CACHE_HOME": "cache",
                                    "NUMBA_CACHE_DIR": "cache/numba",
                                    "LIBERO_CONFIG_PATH": "libero-config"}.items():
                    (data / subdir).mkdir(parents=True, exist_ok=True)
                    env[key] = str(data / subdir)
                # multiprocessing AF_UNIX sockets must stay below Linux's 108-byte limit.
                short_tmp = PROJECT / "t"
                short_tmp.mkdir(exist_ok=True)
                env["TMPDIR"] = str(short_tmp)
                env.pop("GALLIUM_DRIVER", None)
            if spec["kind"] in {"check", "prepare"}:
                env["CUDA_VISIBLE_DEVICES"] = ""
            else:
                query = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
                     "--format=csv,noheader,nounits"], text=True,
                )
                rows = list(csv.reader(query.splitlines()))
                if spec["backend"] == "h100":
                    gpu = None
                    # Hold a per-GPU lease until the child exits, including model-loading time.
                    with lock(root / ".gpu-allocation.lock"):
                        for row in rows:
                            try:
                                candidate = select_gpu([row], "train")
                                lease = lock(root / f".gpu-{candidate}.lock", blocking=False)
                                leases.enter_context(lease)
                            except (RuntimeError, BlockingIOError):
                                continue
                            gpu = candidate
                            break
                    if gpu is None:
                        raise RuntimeError("No idle unleased H100 GPU available")
                else:
                    gpu, used, total, util = map(int, rows[0])
                    # This is also the Windows display GPU; WSL reports several GiB
                    # of graphics allocations without a compute process. The real
                    # policy check measured ~1 GiB peak, so preserve an 8 GiB margin.
                    if total - used < 8192 or util >= 10:
                        raise RuntimeError("PC1 GPU is busy; no other process will be stopped")
                env["CUDA_VISIBLE_DEVICES"] = str(gpu)
                # robosuite validates this value against the physical IDs in
                # CUDA_VISIBLE_DEVICES while MuJoCo later indexes the remapped
                # logical device list. configure_libero performs that handoff.
                env["MUJOCO_EGL_DEVICE_ID"] = str(gpu)
                state["physical_gpu"] = gpu
                write(run / "gpu_before.json", rows)
            mapping = {"{python}": str(python), "{project}": str(run / "source"),
                       "{output}": str(run / "output"), "{data}": str(data),
                       "{run}": str(run)}
            command = []
            for arg in spec["command"]:
                for token, value in mapping.items():
                    arg = arg.replace(token, value)
                command.append(arg)
            write(run / "command.json", command)
            started = time.monotonic()
            state.update(status="running", started_at=time.time(), supervisor_pid=os.getpid())
            with (run / "console.log").open("ab", buffering=0) as log:
                child = subprocess.Popen(command, cwd=run / "source", env=env,
                                         stdin=subprocess.DEVNULL, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                state["child_pid"] = child.pid
                while child.poll() is None:
                    state.update(heartbeat_at=time.time(), elapsed_seconds=time.monotonic()-started)
                    write(run / "state.json", state)
                    if interrupted or (run / "cancel.request").exists():
                        state["status"] = "cancelled"
                        stop_child(child)
                        break
                    if time.monotonic() - started >= spec["timeout_seconds"]:
                        state["status"] = "timed_out"
                        stop_child(child)
                        break
                    time.sleep(1)
                if state["status"] == "running":
                    state["status"] = "succeeded" if child.returncode == 0 else "failed"
                state.update(exit_code=child.returncode, elapsed_seconds=time.monotonic()-started)
        except Exception as exc:
            if child is not None:
                stop_child(child)
            state.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            state["finished_at"] = time.time()
            write(run / "state.json", state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    sub = parser.add_subparsers(dest="action", required=True)
    start = sub.add_parser("submit")
    start.add_argument("spec", type=Path)
    start.add_argument("--budget", type=Path, default=PROJECT / ".runtime/approved-budget.json")
    sub.add_parser("status")
    for name in ["worker", "cancel", "logs"]:
        sub.add_parser(name).add_argument("id")
    args = parser.parse_args()
    default = PROJECT / ".runtime/runs"
    if not PROJECT.is_relative_to(ALLOWED_ROOT) and Path("/data").is_dir():
        default = Path("/data/runs")
    root = (args.root or default).resolve()
    if args.action == "submit":
        result = submit(root, read(args.spec), args.budget)
    elif args.action == "worker":
        worker(root, args.id)
        return
    elif args.action == "status":
        result = records(root)
        for r in result:
            if r["status"] not in FINAL:
                r["heartbeat_age_seconds"] = time.time() - r.get("heartbeat_at", r["created_at"])
                r["needs_inspection"] = r["heartbeat_age_seconds"] > 60
    else:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", args.id):
            raise ValueError("Invalid run ID")
        run = root / args.id
        state = read(run / "state.json")
        if args.action == "cancel":
            if state["status"] not in FINAL:
                (run / "cancel.request").touch()
            result = {"id": args.id, "cancel_requested": state["status"] not in FINAL}
        else:
            p = run / "console.log"
            if p.exists():
                with p.open("rb") as f:
                    f.seek(max(0, p.stat().st_size - 16000))
                    print(f.read().decode(errors="replace"))
            return
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
