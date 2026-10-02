#!/usr/bin/env bash
# Run on PC1 after committing source changes. Runtime files are never transferred.
set -euo pipefail
cd "$(dirname "$0")/.."
test -z "$(git status --porcelain)" || { echo 'Commit local changes first.' >&2; exit 1; }
test "$(git branch --show-current)" = main || { echo 'Switch to main first.' >&2; exit 1; }
stage=/mnt/d/Robotics/smolvla-sim/sync
mkdir -p "$stage"
git bundle create "$stage/source.bundle" main
target=/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model/smolvla-sim
/mnt/c/Windows/System32/OpenSSH/scp.exe -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ConnectTimeout=30 -o IPQoS=none D:/Robotics/smolvla-sim/sync/source.bundle \
  "mlspace-sr006:$target/.runtime/source.bundle" </dev/null
bash scripts/h100_ssh.sh "bash '$target/scripts/receive_h100.sh'" </dev/null
