"""Extract LeRobot console metrics and render the training loss curve."""

import argparse
import csv
import json
import re
from pathlib import Path

METRIC = re.compile(
    r"INFO [^\r\n]*?loss:(?P<loss>[0-9.eE+-]+) "
    r"grdn:(?P<grad>[0-9.eE+-]+) lr:(?P<lr>[0-9.eE+-]+)"
)


def parse_metrics(text, log_frequency=50):
    return [
        {
            "step": index * log_frequency,
            "loss": float(match["loss"]),
            "grad_norm": float(match["grad"]),
            "learning_rate": float(match["lr"]),
        }
        for index, match in enumerate(METRIC.finditer(text), start=1)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--log-frequency", type=int, default=50)
    args = parser.parse_args()
    rows = parse_metrics(args.log.read_text(errors="replace"), args.log_frequency)
    if not rows:
        raise SystemExit("No LeRobot training metrics found")

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "loss.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    steps = [row["step"] for row in rows]
    losses = [row["loss"] for row in rows]
    window = min(20, len(losses))
    smooth = [sum(losses[max(0, i - window + 1) : i + 1]) / min(window, i + 1)
              for i in range(len(losses))]
    fig, axis = plt.subplots(figsize=(8, 4.5))
    axis.plot(steps, losses, color="#8cb6d9", linewidth=0.8, label="logged loss")
    axis.plot(steps, smooth, color="#155a8a", linewidth=1.8,
              label=f"moving mean ({window} points)")
    axis.set(xlabel="Training step", ylabel="Loss", title="SmolVLA fine-tuning on LIBERO Object")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(args.output / "loss.png", dpi=160)
    plt.close(fig)

    summary = {
        "log_frequency": args.log_frequency,
        "points": len(rows),
        "first": rows[0],
        "last": rows[-1],
        "minimum_loss": min(losses),
    }
    (args.output / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
