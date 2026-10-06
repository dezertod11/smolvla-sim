#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { echo 'Create .env from .env.example first.'; exit 1; }
if test "${1:-}" = build; then
  exec bash scripts/docker.sh compose -f compose.yaml -f compose.wsl.yaml \
    -f compose.build.yaml "$@"
fi
exec bash scripts/docker.sh compose "$@"
