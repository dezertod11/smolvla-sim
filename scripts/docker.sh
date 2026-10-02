#!/usr/bin/env bash
# Isolated public-registry Docker config; preserves the user's Desktop credentials.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
export DOCKER_CONFIG="$root/.runtime/docker-cli"
mkdir -p "$DOCKER_CONFIG"
if ! test -f "$DOCKER_CONFIG/config.json"; then
  printf '{}\n' > "$DOCKER_CONFIG/config.json"
fi
exec /usr/bin/docker "$@"
