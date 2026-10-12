"""Load one real training batch through LeRobot without creating the policy."""

import json
import os
from pathlib import Path

import draccus
from lerobot.configs.train import TrainPipelineConfig
from lerobot.datasets.factory import make_dataset
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig  # noqa: F401
from torch.utils.data import DataLoader

from train_managed import prepare


def main():
    project = Path(__file__).resolve().parents[1]
    data = Path(os.environ["ROBOTICS_DATA_DIR"])
    raw = json.loads((project / "configs/train_libero_object.json").read_text())
    resolved = prepare(raw, data, data / "batch-check-unused", steps=1, batch_size=2)
    cfg = draccus.decode(TrainPipelineConfig, resolved)
    cfg.validate()
    dataset = make_dataset(cfg)
    batch = next(iter(DataLoader(dataset, batch_size=2, num_workers=0)))
    evidence = {
        "dataset_samples": len(dataset),
        "episodes": len(cfg.dataset.episodes),
        "batch_keys": sorted(batch),
        "state_shape": list(batch["observation.state"].shape),
        "action_shape": list(batch["action"].shape),
        "image_shape": list(batch["observation.images.image"].shape),
        "image2_shape": list(batch["observation.images.image2"].shape),
    }
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
