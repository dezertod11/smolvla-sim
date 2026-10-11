#!/usr/bin/env bash
# PC1 WSL entry point; the H100 SSH key stays on the Windows host.
set -euo pipefail
cd "$(dirname "$0")/.."
backend=${1:?Use pc1 or h100 followed by jobs.py arguments}
shift
case "$backend" in
  pc1) exec bash scripts/pc1.sh exec -T dev python scripts/jobs.py "$@" ;;
  h100)
    target=/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model/smolvla-sim
    printf -v command '%q ' .venv/bin/python scripts/jobs.py "$@"
    exec bash scripts/h100_ssh.sh "cd '$target' && $command"
    ;;
  *) echo 'Expected pc1 or h100' >&2; exit 2 ;;
esac
