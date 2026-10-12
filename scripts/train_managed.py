"""Prepare an explicit training config, then invoke the pinned lerobot-train.

Use through jobs.py after budget approval. --validate-only does no downloads,
model loading, GPU allocation or training.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def prepare(config, data, output, steps, batch_size):
    config = json.loads(json.dumps(config))
    config["dataset"]["root"] = str(data / "datasets/libero_object")
    config["policy"]["pretrained_path"] = str(data / "models/base")
    config["policy"]["vlm_model_name"] = str(data / "models/vlm")
    config["output_dir"] = str(output)
    config["steps"] = steps
    config["batch_size"] = batch_size
    config["log_freq"] = min(50, steps)
    config["save_freq"] = min(1000, steps)
    config["num_workers"] = 4
    config["job_name"] = output.parent.name
    config["resume"] = False
    config["policy"]["push_to_hub"] = False
    config["wandb"]["enable"] = True
    config["wandb"]["mode"] = "offline"
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/train_libero_object.json"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1:
        parser.error("steps and batch size must be positive")
    cfg = prepare(json.loads(args.config.read_text()), args.data.resolve(),
                  args.output.resolve(), args.steps, args.batch_size)
    # The policy module registers the dataclass with draccus.
    import draccus
    from lerobot.configs.train import TrainPipelineConfig
    from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig  # noqa: F401

    parsed = draccus.decode(TrainPipelineConfig, cfg)
    parsed.validate()
    assert parsed.policy.input_features["observation.state"].shape == (8,) or list(
        parsed.policy.input_features["observation.state"].shape
    ) == [8]
    if args.validate_only:
        print(json.dumps({"valid": True, "episodes": len(parsed.dataset.episodes),
                          "steps": parsed.steps, "batch_size": parsed.batch_size,
                          "output": str(parsed.output_dir)}, indent=2))
        return
    if not (args.data / "models/base/model.safetensors").is_file():
        raise SystemExit("Pinned base model missing; run download_checkpoint.py base first")
    if args.output.exists():
        raise SystemExit("Refusing to overwrite an existing training output")
    config_path = args.output.parent / "effective_train_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg, indent=2) + "\n")
    os.environ["ACCELERATE_MIXED_PRECISION"] = "bf16"
    os.environ["WANDB_MODE"] = "offline"
    command = [sys.executable, "-m", "lerobot.scripts.lerobot_train",
               f"--config_path={config_path}"]
    print("Launching pinned lerobot-train", flush=True)
    raise SystemExit(subprocess.call(command))


if __name__ == "__main__":
    main()
