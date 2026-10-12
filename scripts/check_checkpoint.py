"""Reload a saved checkpoint and run one real BF16 forward pass."""

import argparse
import json
from collections import Counter
from pathlib import Path

import draccus
import torch
from lerobot.configs.train import TrainPipelineConfig
from lerobot.datasets.factory import make_dataset
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig  # noqa: F401
from torch.utils.data import DataLoader
from train_managed import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    checkpoint = args.checkpoint.resolve()
    if not (checkpoint / "model.safetensors").is_file():
        raise SystemExit(f"Checkpoint is incomplete: {checkpoint}")
    project = Path(__file__).resolve().parents[1]
    raw = json.loads((project / "configs/train_libero_object.json").read_text())
    config = prepare(raw, args.data.resolve(), args.data / "reload-unused", 1, 2, 2)
    config["policy"]["pretrained_path"] = str(checkpoint)
    cfg = draccus.decode(TrainPipelineConfig, config)
    cfg.validate()
    dataset = make_dataset(cfg)
    policy = make_policy(cfg.policy, ds_meta=dataset.meta, rename_map=cfg.rename_map).eval()
    overrides = {
        "device_processor": {"device": str(policy.config.device)},
        "rename_observations_processor": {"rename_map": cfg.rename_map},
    }
    preprocessor, _ = make_pre_post_processors(
        cfg.policy, pretrained_path=str(checkpoint), preprocessor_overrides=overrides
    )
    batch = next(iter(DataLoader(dataset, batch_size=2, num_workers=0)))
    batch = preprocessor(batch)
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        autocast_enabled = torch.is_autocast_enabled("cuda")
        loss, output = policy.forward(batch)
    torch.cuda.synchronize()
    evidence = {
        "checkpoint": str(checkpoint),
        "loss": float(loss),
        "output_keys": sorted(output),
        "parameter_dtypes": dict(Counter(str(p.dtype) for p in policy.parameters())),
        "trainable_parameters": sum(p.numel() for p in policy.parameters() if p.requires_grad),
        "total_parameters": sum(p.numel() for p in policy.parameters()),
        "bf16_autocast": autocast_enabled,
        "peak_cuda_bytes": torch.cuda.max_memory_allocated(),
    }
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
