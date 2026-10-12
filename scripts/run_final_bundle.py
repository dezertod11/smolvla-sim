"""Run a fixed bundle of final evaluations and benchmarks on one leased GPU."""

import argparse
import subprocess
import sys
from pathlib import Path

ACTIONS = {
    "eval-bf16-n1": ("eval", "bf16", "1"),
    "eval-bf16-n10": ("eval", "bf16", "10"),
    "eval-bf16-n50": ("eval", "bf16", "50"),
    "eval-int8-n10": ("eval", "int8", "10"),
    "bench-bf16-cuda": ("benchmark", "bf16", "cuda"),
    "bench-int8-cuda": ("benchmark", "int8", "cuda"),
    "bench-bf16-cpu": ("benchmark", "bf16", "cpu"),
}


def command(action, checkpoint, data, output):
    kind, precision, value = ACTIONS[action]
    if kind == "eval":
        return [
            sys.executable, "scripts/eval_managed.py",
            "--checkpoint", str(checkpoint), "--data", str(data),
            "--output", str(output / action), "--n-action-steps", value,
            "--precision", precision,
        ]
    warmup, iterations = ("2", "5") if value == "cpu" else ("5", "20")
    return [
        sys.executable, "scripts/benchmark_policy.py",
        "--checkpoint", str(checkpoint), "--data", str(data),
        "--output", str(output / action), "--device", value,
        "--precision", precision, "--warmup", warmup, "--iterations", iterations,
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--action", action="append", choices=sorted(ACTIONS), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    for action in args.action:
        print(f"FINAL_BUNDLE_START {action}", flush=True)
        subprocess.run(command(action, args.checkpoint, args.data, args.output), check=True)
        print(f"FINAL_BUNDLE_DONE {action}", flush=True)


if __name__ == "__main__":
    main()
