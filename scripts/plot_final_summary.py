"""Plot the committed evaluation results without recomputing experiments."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

plt.switch_backend("Agg")


LABELS = {
    "reference-bf16-n10": "Reference\nBF16, n=10",
    "own-bf16-n1": "Own\nBF16, n=1",
    "own-bf16-n10": "Own\nBF16, n=10",
    "own-bf16-n50": "Own\nBF16, n=50",
    "own-int8-n10": "Own\nINT8, n=10",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts/results/summary/evaluation_summary.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/results/summary/evaluation_comparison.png"),
    )
    args = parser.parse_args()
    results = json.loads(args.input.read_text(encoding="utf-8"))
    labels = [LABELS[item["label"]] for item in results]
    success = [100 * item["success_rate"] for item in results]
    seconds = [item["mean_episode_seconds"] for item in results]
    colors = ["#64748b", "#3b82f6", "#16a34a", "#f59e0b", "#dc2626"]

    figure, success_axis = plt.subplots(figsize=(12, 5.6))
    positions = range(len(results))
    bars = success_axis.bar(positions, success, color=colors, width=0.66)
    success_axis.set_ylabel("Success rate, %")
    success_axis.set_ylim(0, 110)
    success_axis.set_xticks(list(positions), labels)
    success_axis.grid(axis="y", alpha=0.22)
    success_axis.bar_label(bars, labels=[f"{value:.0f}%" for value in success], padding=3)

    time_axis = success_axis.twinx()
    time_axis.plot(positions, seconds, color="#111827", marker="o", linewidth=2)
    time_axis.set_ylabel("Mean episode time, s")
    time_axis.set_ylim(0, max(seconds) * 1.25)
    for position, value in zip(positions, seconds, strict=True):
        time_axis.annotate(
            f"{value:.1f}s",
            (position, value),
            xytext=(0, -18),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )

    figure.suptitle("LIBERO Object: quality and episode time (10 tasks × 10 episodes)")
    figure.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180, bbox_inches="tight")
    print(args.output)


if __name__ == "__main__":
    main()
