#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime/control
if ! tmux has-session -t smolvla-control 2>/dev/null; then
  tmux new-session -d -s smolvla-control -c "$PWD" \
    'python3 scripts/control.py worker >>.runtime/control/worker.log 2>&1'
fi
echo 'Project control worker: tmux session smolvla-control'
