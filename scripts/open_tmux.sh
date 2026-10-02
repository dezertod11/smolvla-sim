#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
session=smolvla
if ! tmux has-session -t "=$session" 2>/dev/null; then
  tmux new-session -d -s "$session" -c "$root"
fi
if test "${1:-}" = --ensure; then exit 0; fi
if test -n "${TMUX:-}"; then
  exec tmux switch-client -t "=$session"
fi
exec tmux attach-session -t "=$session"
