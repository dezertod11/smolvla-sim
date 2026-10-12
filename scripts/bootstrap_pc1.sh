#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo "Docker CLI is required" >&2; exit 1; }
test -f .env || cp .env.example .env
data_dir=$(sed -n 's/^ROBOTICS_DATA_DIR=//p' .env | tail -n 1)
test -n "$data_dir" || { echo "Set ROBOTICS_DATA_DIR in .env" >&2; exit 1; }
mkdir -p "$data_dir"/{cache,huggingface,libero-config,models}
if ! bash scripts/docker.sh volume inspect smolvla-sim-home >/dev/null 2>&1; then
  bash scripts/docker.sh volume create smolvla-sim-home >/dev/null
fi
bash scripts/docker.sh compose -f compose.yaml -f compose.wsl.yaml \
  -f compose.build.yaml build dev
echo "PC1 bootstrap complete. Download the checkpoint, then run: bash scripts/pc1.sh up runtime"
