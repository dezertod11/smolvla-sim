"""Run the frozen LIBERO protocol with explicit BF16 or audited INT8 policy loading."""

import argparse
import json
import sys
from pathlib import Path

import torch

from smolvla_service.features import camera_rename_map


def checkpoint_rename_map(checkpoint):
    config = json.loads((Path(checkpoint) / "config.json").read_text())
    return camera_rename_map(config.get("input_features", {}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--n-action-steps", type=int, choices=[1, 10, 50], required=True)
    parser.add_argument("--precision", choices=["bf16", "int8"], required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    protocol = json.loads((project / "configs/evaluation_protocol.json").read_text())
    episodes = 1 if args.development else protocol["episodes_per_task"]
    seed = protocol["development_start_seed"] if args.development else protocol["final_start_seed"]
    task_ids = protocol["task_ids"]
    rename_map = checkpoint_rename_map(args.checkpoint)
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite evaluation output: {args.output}")

    from configure_libero import configure

    configure()
    import lerobot.scripts.lerobot_eval as evaluation

    quantization_report = None
    if args.precision == "int8":
        from smolvla_service.quantization import quantize_linear_int8

        original_make_policy = evaluation.make_policy

        def make_int8_policy(*policy_args, **policy_kwargs):
            nonlocal quantization_report
            policy = original_make_policy(*policy_args, **policy_kwargs)
            policy, quantization_report = quantize_linear_int8(policy)
            return policy

        evaluation.make_policy = make_int8_policy

    torch.set_autocast_dtype("cuda", torch.bfloat16)
    sys.argv = [
        "lerobot-eval",
        f"--policy.path={args.checkpoint}",
        "--policy.device=cuda",
        "--policy.use_amp=true",
        f"--policy.n_action_steps={args.n_action_steps}",
        f"--policy.vlm_model_name={args.data / 'models/vlm'}",
        "--env.type=libero",
        f"--env.task={protocol['suite']}",
        f"--env.task_ids={json.dumps(task_ids)}",
        f"--env.max_parallel_tasks={protocol['max_parallel_tasks']}",
        f"--eval.batch_size={protocol['batch_size']}",
        f"--eval.n_episodes={episodes}",
        f"--seed={seed}",
        f"--output_dir={args.output}",
    ]
    if rename_map:
        sys.argv.append(f"--rename_map={json.dumps(rename_map)}")
    evaluation.eval_main()
    evidence = {
        "checkpoint": args.checkpoint,
        "precision": args.precision,
        "autocast_dtype": str(torch.get_autocast_dtype("cuda")),
        "n_action_steps": args.n_action_steps,
        "task_ids": task_ids,
        "episodes_per_task": episodes,
        "seed": seed,
        "quantization": quantization_report,
        "rename_map": rename_map,
    }
    (args.output / "protocol.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
