#!/usr/bin/env bash
# Run on PC1 WSL. Windows OpenSSH uses PC1's existing key and network route.
set -euo pipefail
ssh_bin=/mnt/c/Windows/System32/OpenSSH/ssh.exe
test -x "$ssh_bin" || { echo 'This launcher runs on PC1 WSL.' >&2; exit 1; }
target=/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model/smolvla-sim
if test "${1:-}" = --interactive; then
  exec "$ssh_bin" -tt -o StrictHostKeyChecking=yes -o ConnectTimeout=30 -o IPQoS=none \
    mlspace-sr006 "cd '$target' && exec bash -l"
fi
exec "$ssh_bin" -T -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ConnectTimeout=30 -o IPQoS=none mlspace-sr006 "$@"
