"""Measure forced SmolVLA forward latency after warm-up on a real LIBERO observation."""

import argparse
import json
import statistics
import time
from pathlib import Path

import draccus
import torch
from lerobot.configs.policies import PreTrainedConfig
from lerobot.configs.train import TrainPipelineConfig
from lerobot.datasets.factory import make_dataset
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig  # noqa: F401
from torch.utils.data import DataLoader
from train_managed import prepare

from smolvla_service.features import camera_rename_map
from smolvla_service.metrics import percentile
from smolvla_service.quantization import quantize_linear_int8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], required=True)
    parser.add_argument("--precision", choices=["bf16", "int8"], required=True)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if args.precision == "int8" and args.device != "cuda":
        raise SystemExit("bitsandbytes INT8 benchmark requires CUDA")
    if args.warmup < 1 or args.iterations < 2:
        raise SystemExit("Use at least one warm-up and two measured iterations")
    project = Path(__file__).resolve().parents[1]
    raw = json.loads((project / "configs/train_libero_object.json").read_text())
    config = prepare(raw, args.data.resolve(), args.data / "benchmark-unused", 1, 1, 2, 0)
    cfg = draccus.decode(TrainPipelineConfig, config)
    cfg.validate()
    dataset = make_dataset(cfg)
    policy_cfg = PreTrainedConfig.from_pretrained(args.checkpoint)
    policy_cfg.pretrained_path = str(args.checkpoint.resolve())
    policy_cfg.vlm_model_name = str(args.data / "models/vlm")
    policy_cfg.device = args.device
    rename_map = camera_rename_map(policy_cfg.input_features)
    policy = make_policy(
        policy_cfg, ds_meta=dataset.meta, rename_map=rename_map
    ).eval()
    quantization = None
    if args.precision == "int8":
        policy, quantization = quantize_linear_int8(policy)
    overrides = {
        "device_processor": {"device": args.device},
        "rename_observations_processor": {"rename_map": rename_map},
        "tokenizer_processor": {"tokenizer_name": str(args.data / "models/vlm")},
    }
    preprocessor, _ = make_pre_post_processors(
        policy_cfg, pretrained_path=str(args.checkpoint), preprocessor_overrides=overrides
    )
    source_batch = next(iter(DataLoader(dataset, batch_size=1, num_workers=0)))
    batch = {
        "observation.images.image": source_batch["observation.images.image"][:, -1],
        "observation.images.image2": source_batch["observation.images.image2"][:, -1],
        "observation.state": source_batch["observation.state"][:, -1],
        "task": source_batch["task"],
    }
    batch = preprocessor(batch)

    def synchronize():
        if args.device == "cuda":
            torch.cuda.synchronize()

    def infer():
        # Reset the action queue so every sample measures a model forward, not a cached action.
        policy.reset()
        with torch.inference_mode(), torch.autocast(args.device, dtype=torch.bfloat16):
            policy.select_action(batch)
        synchronize()

    for _ in range(args.warmup):
        infer()
    if args.device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    timings = []
    for _ in range(args.iterations):
        synchronize()
        started = time.perf_counter_ns()
        infer()
        timings.append((time.perf_counter_ns() - started) / 1_000_000)

    args.output.mkdir(parents=True, exist_ok=False)
    if args.precision == "int8":
        serialized = args.output / "int8_state_dict.pt"
        torch.save(policy.state_dict(), serialized)
        serialized_bytes = serialized.stat().st_size
    else:
        serialized_bytes = (args.checkpoint / "model.safetensors").stat().st_size
    result = {
        "checkpoint": str(args.checkpoint.resolve()),
        "device": args.device,
        "precision": args.precision,
        "warmup": args.warmup,
        "iterations": args.iterations,
        "latency_ms": {
            "median": statistics.median(timings),
            "p50": percentile(timings, 0.50),
            "p95": percentile(timings, 0.95),
            "samples": timings,
        },
        "serialized_bytes": serialized_bytes,
        "peak_cuda_bytes": torch.cuda.max_memory_allocated() if args.device == "cuda" else None,
        # infer() requests BF16 explicitly.  Reporting PyTorch's process default
        # here used to say FP16 on CUDA even though the timed context was BF16.
        "autocast_dtype": str(torch.bfloat16),
        "quantization": quantization,
    }
    (args.output / "benchmark.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
