#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || cp .env.example .env
data_dir=$(sed -n 's/^ROBOTICS_DATA_DIR=//p' .env | tail -n 1)
test -n "$data_dir" || { echo "Set ROBOTICS_DATA_DIR in .env" >&2; exit 1; }
destination="$data_dir/models/own-final"
base=https://github.com/dezertod11/smolvla-sim/releases/download/smolvla-libero-object-v1
mkdir -p "$destination"
while read -r checksum filename; do
  target="$destination/$filename"
  if ! test -f "$target" || \
    ! echo "$checksum  $target" | sha256sum -c - >/dev/null 2>&1; then
    curl --fail --location --retry 3 --output "$target.part" "$base/$filename"
    mv "$target.part" "$target"
  fi
  echo "$checksum  $target" | sha256sum -c -
done < configs/own_checkpoint.sha256
echo "Verified checkpoint: $destination"
