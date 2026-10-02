#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
allowed=/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model
case "$(pwd -P)" in "$allowed"/*) ;; *) echo 'Outside permitted workspace'; exit 1;; esac
test -d .git || { echo 'Initialize the source checkout first.'; exit 1; }
test -z "$(git status --porcelain)" || { echo 'H100 has local changes; sync stopped.'; exit 1; }
test "$(git branch --show-current)" = main || { echo 'H100 is not on main'; exit 1; }
git fetch .runtime/source.bundle main
git merge --ff-only FETCH_HEAD
echo 'Source updated. Run bootstrap_h100.sh if dependency locks changed.'
