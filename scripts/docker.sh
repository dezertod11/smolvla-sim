#!/usr/bin/env bash
# Isolated public-registry Docker config; preserves the user's Desktop credentials.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
export DOCKER_CONFIG="$root/.runtime/docker-cli"
mkdir -p "$DOCKER_CONFIG"
if ! test -f "$DOCKER_CONFIG/config.json"; then
  printf '{}\n' > "$DOCKER_CONFIG/config.json"
fi
# This project uses the single Docker Desktop engine on PC1.
# Fail before a build/pull if another engine owns the WSL socket.
unset DOCKER_CONTEXT DOCKER_HOST
endpoint=unix:///var/run/docker.sock
docker_cli=/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker
test -x "$docker_cli" || {
  echo 'Start Docker Desktop on PC1 and enable its Ubuntu WSL integration.' >&2
  exit 1
}
server_os=$(timeout 10 "$docker_cli" --host "$endpoint" info --format '{{.OperatingSystem}}') || {
  echo 'Docker Desktop is not responding. No command was executed.' >&2
  exit 1
}
case "$server_os" in
  *Docker\ Desktop*) ;;
  *) echo 'Unexpected Docker Engine: this project requires Docker Desktop on PC1.' >&2; exit 1 ;;
esac
exec "$docker_cli" --host "$endpoint" "$@"
