"""Run inside the permitted H100 workspace on a currently idle allowed GPU."""

import argparse
import csv
import os
import subprocess
from pathlib import Path

ALLOWED_ROOT = Path("/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model")


def select_gpu(rows, mode, requested=None):
    allowed = set(range(1, 8))  # User authorized idle GPU 1–7 for all work, 2026-10-12.
    if requested is not None and requested not in allowed:
        raise ValueError(f"GPU {requested} is forbidden for {mode}")
    for row in rows:
        index, used, total, utilization = map(int, row)
        if index not in allowed or (requested is not None and index != requested):
            continue
        if used < 1024 and total - used >= 16000 and utilization < 10:
            return index
    raise RuntimeError("No idle allowed GPU. No process was started; retry later.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "smoke"], default="train")
    parser.add_argument("--gpu", type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    if not project.is_relative_to(ALLOWED_ROOT.resolve()):
        raise SystemExit(f"H100 project must be below {ALLOWED_ROOT}")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Supply a command after --")
    query = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"], text=True
    )
    gpu = select_gpu(csv.reader(query.splitlines()), args.mode, args.gpu)
    runtime = project / ".runtime"
    for name in ["huggingface", "cache", "tmp", "outputs", "libero-config", "home"]:
        (runtime / name).mkdir(parents=True, exist_ok=True)
    os.environ.update({
        "CUDA_VISIBLE_DEVICES": str(gpu), "HF_HOME": str(runtime / "huggingface"),
        "XDG_CACHE_HOME": str(runtime / "cache"), "TMPDIR": str(runtime / "tmp"),
        "ROBOTICS_DATA_DIR": str(runtime), "LIBERO_CONFIG_PATH": str(runtime / "libero-config"),
        "WANDB_MODE": "offline", "WANDB_DIR": str(runtime / "outputs"),
        "HOME": str(runtime / "home"), "NUMBA_CACHE_DIR": str(runtime / "cache/numba"),
        "PYTHONPATH": str(project / "src"),
    })
    os.environ.pop("GALLIUM_DRIVER", None)
    os.chdir(project)
    print(f"Selected physical GPU {gpu}; application sees cuda:0", flush=True)
    os.execvpe(command[0], command, os.environ)


if __name__ == "__main__":
    main()
