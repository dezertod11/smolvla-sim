#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
allowed=/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model
case "$(pwd -P)" in "$allowed"/*) ;; *) echo 'Outside the permitted H100 workspace'; exit 1;; esac
root=$(pwd -P)
mkdir -p .runtime/{cache,tmp,huggingface,outputs,libero-config}
export XDG_CACHE_HOME="$root/.runtime/cache"
export UV_CACHE_DIR="$root/.runtime/cache/uv"
export PIP_CACHE_DIR="$root/.runtime/cache/pip"
export TMPDIR="$root/.runtime/tmp"
export HF_HOME="$root/.runtime/huggingface"
test -f requirements.h100.lock || { echo 'Missing H100 dependency lock'; exit 1; }
free_kb=$(df -Pk . | awk 'NR==2 {print $4}')
test "$free_kb" -ge 20971520 || { echo 'At least 20 GiB free space required'; exit 1; }
python3.12 --version
if ! .venv/bin/python -c 'import encodings' >/dev/null 2>&1; then
  uv venv --allow-existing --python "$(readlink -f "$(command -v python3.12)")" .venv
fi
uv pip install --python .venv/bin/python --index-strategy unsafe-best-match \
  --extra-index-url https://download.pytorch.org/whl/cu126 -r requirements.h100.lock
uv pip install --python .venv/bin/python --no-deps -e .
uv pip check --python .venv/bin/python
echo 'H100 environment installed. Use scripts/h100_run.py to select an allowed idle GPU.'
