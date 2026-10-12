"""Validate raw evaluation artifacts and build a compact comparison table."""

import argparse
import json
from pathlib import Path

from smolvla_service.evaluation import summarize


def load_run(value):
    label, separator, raw_path = value.partition("=")
    if not separator or not label:
        raise ValueError("Each run must be LABEL=DIRECTORY")
    path = Path(raw_path)
    report = json.loads((path / "eval_info.json").read_text())
    protocol = json.loads((path / "protocol.json").read_text())
    summary = summarize(report)
    return {
        "label": label,
        "precision": protocol["precision"],
        "n_action_steps": protocol["n_action_steps"],
        **summary,
        "mean_episode_seconds": report["overall"]["eval_ep_s"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, metavar="LABEL=DIRECTORY")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [load_run(value) for value in args.run]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "evaluation_summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    lines = [
        "| Variant | Precision | n_action_steps | Success | Mean episode, s |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['precision']} | {row['n_action_steps']} | "
            f"{row['successes']}/{row['episodes']} ({row['success_rate']:.0%}) | "
            f"{row['mean_episode_seconds']:.2f} |"
        )
    (args.output / "evaluation_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
