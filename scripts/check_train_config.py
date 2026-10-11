"""Check the experiment on CPU, offline, without creating a policy or dataset."""

import json
import os
from pathlib import Path


def main():
    # These affect this checker only, not Docker, the shell or the saved config.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    print("Loading LeRobot config classes on CPU; no weights or network...", flush=True)

    import torch
    from lerobot.configs.train import TrainPipelineConfig
    from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
    from lerobot.processor import (
        NormalizerProcessorStep,
        PolicyProcessorPipeline,
        RenameObservationsProcessorStep,
        UnnormalizerProcessorStep,
    )

    torch.set_num_threads(2)

    root = Path(__file__).resolve().parents[1]
    path = root / "configs/train_libero_object.json"
    raw = json.loads(path.read_text())
    manifest = json.loads((root / "configs/libero_object_episodes.json").read_text())
    artifacts = json.loads((root / "configs/artifacts.json").read_text())
    assert manifest["dataset"] == artifacts["dataset"], "Stale episode manifest"
    assert manifest["base"] == artifacts["base"], "Stale base model revision"
    for key in ("repo_id", "revision"):
        assert raw["dataset"][key] == artifacts["dataset"][key]
    assert raw["dataset"]["episodes"] == manifest["selection"]["episode_indices"]
    assert len(set(raw["dataset"]["episodes"])) == 454
    assert raw["rename_map"] == manifest["rename_map"]
    assert raw["policy"]["pretrained_path"] == ".runtime/models/base"
    for value in (raw["dataset"]["root"], raw["policy"]["pretrained_path"], raw["output_dir"]):
        location = Path(value)
        assert not location.is_absolute() and location.parts[0] == ".runtime"
        assert ".." not in location.parts

    # The same JSON parser as lerobot-train. Override device only in memory:
    # parsing must not require a GPU, local weights, network, or a training call.
    cfg = TrainPipelineConfig.from_pretrained(
        path, cli_args=["--policy.device=cpu", "--policy.use_amp=false"]
    )
    cfg.validate()
    assert isinstance(cfg.policy, SmolVLAConfig)
    assert str(cfg.policy.pretrained_path) == ".runtime/models/base"
    assert cfg.policy.input_features["observation.state"].shape == (8,)
    assert cfg.policy.output_features["action"].shape == (7,)
    assert set(cfg.policy.image_features) == set(cfg.rename_map.values())
    assert all(feature.shape == (3, 256, 256) for feature in cfg.policy.image_features.values())
    assert cfg.policy.n_action_steps == 10 and cfg.policy.chunk_size == 50
    assert cfg.wandb.mode == "offline" and not cfg.policy.push_to_hub
    assert cfg.wandb.enable and cfg.wandb.disable_artifact
    assert cfg.env is None and cfg.eval_freq == 0
    assert cfg.dataset.use_imagenet_stats is False

    # Known synthetic statistics test broadcasting over a batch and action chunk.
    # Actual training will use the pinned dataset's global meta/stats.json.
    stats = {
        "observation.state": {"mean": [1.0] * 8, "std": [2.0] * 8},
        "action": {"mean": [2.0] * 7, "std": [4.0] * 7},
    }
    normalizer = NormalizerProcessorStep(
        features={**cfg.policy.input_features, **cfg.policy.output_features},
        norm_map=cfg.policy.normalization_mapping, stats=stats, device="cpu",
    )
    # Explicit dataset statistics must supersede the base checkpoint's 6D state.
    normalizer.load_state_dict({"observation.state.mean": torch.zeros(6)})
    preprocess = PolicyProcessorPipeline(steps=[
        RenameObservationsProcessorStep(rename_map=cfg.rename_map), normalizer,
    ])
    postprocess = PolicyProcessorPipeline(steps=[UnnormalizerProcessorStep(
        features=cfg.policy.output_features, norm_map=cfg.policy.normalization_mapping,
        stats=stats, device="cpu",
    )])
    batch = {
        "observation.state": torch.full((2, 8), 5.0),
        "action": torch.full((2, 50, 7), 10.0),
        "observation.images.image": torch.zeros(2, 3, 256, 256),
        "observation.images.image2": torch.ones(2, 3, 256, 256),
    }
    processed = preprocess(batch)
    torch.testing.assert_close(processed["observation.state"], torch.full((2, 8), 2.0))
    torch.testing.assert_close(processed["action"], torch.full((2, 50, 7), 2.0))
    for original, renamed in cfg.rename_map.items():
        assert original not in processed
        torch.testing.assert_close(processed[renamed], batch[original])
    restored = postprocess({"action": processed["action"]})
    torch.testing.assert_close(restored["action"], batch["action"])
    assert cfg.optimizer.lr == cfg.policy.optimizer_lr
    print("PASS: pinned artifacts, 454 episodes, local H100 paths")
    print("PASS: LeRobot JSON parsing, optimizer/scheduler presets, CPU validation")
    print("PASS: two-camera rename, 8D state normalization, 7D action round trip")
    print("No weights, dataset, tokenizer, CUDA operations or training were loaded/run.")


if __name__ == "__main__":
    main()
