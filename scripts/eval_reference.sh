#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
data=${ROBOTICS_DATA_DIR:-/data}
python scripts/configure_libero.py
python scripts/download_checkpoint.py reference
exec lerobot-eval \
  --policy.path="$data/models/reference" \
  --policy.device=cuda \
  --policy.n_action_steps=10 \
  --env.type=libero --env.task=libero_object --env.task_ids='[0]' \
  --env.max_parallel_tasks=1 --eval.batch_size=1 --eval.n_episodes=1 \
  --seed=0 --output_dir="$data/outputs/reference-smoke-$(date +%Y%m%dT%H%M%S)"
