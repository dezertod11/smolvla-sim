#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set +u
source /opt/ros/jazzy/setup.bash
set -u
python -m pytest -q
ruff check .
python scripts/runtime_check.py "$@"
python scripts/libero_check.py
