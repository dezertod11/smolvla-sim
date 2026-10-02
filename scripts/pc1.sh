#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { echo 'Create .env from .env.example first.'; exit 1; }
exec bash scripts/docker.sh compose "$@"
