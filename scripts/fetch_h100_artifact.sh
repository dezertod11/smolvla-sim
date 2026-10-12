#!/usr/bin/env bash
# Copy a fixed, completed H100 artifact into the external PC1 data directory.
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  vlm)
    remote=.runtime/models/vlm
    destination=/mnt/d/Robotics/smolvla-sim/models/vlm
    ;;
  own-final)
    remote=.runtime/jobs/h100/h100-train-main-001/output/checkpoints/030000/pretrained_model
    destination=/mnt/d/Robotics/smolvla-sim/models/own-final
    ;;
  *)
    echo "Usage: $0 vlm|own-final" >&2
    exit 2
    ;;
esac
test ! -e "$destination" || { echo "Refusing to overwrite $destination" >&2; exit 1; }
temporary="${destination}.transfer"
test ! -e "$temporary" || { echo "Remove incomplete $temporary after inspection" >&2; exit 1; }
mkdir -p "$temporary"
target=/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model/smolvla-sim
if ! bash scripts/h100_ssh.sh "tar -C '$target/$remote' -cf - ." </dev/null \
  | tar -C "$temporary" -xf -; then
  echo "Transfer failed; inspect $temporary before removing it" >&2
  exit 1
fi
test -f "$temporary/config.json" && test -f "$temporary/model.safetensors"
find "$temporary" -type f -not -path '*/.cache/*' -print0 \
  | sort -z | xargs -0 sha256sum >"$temporary/TRANSFER_SHA256.txt"
mv "$temporary" "$destination"
du -sh "$destination"
