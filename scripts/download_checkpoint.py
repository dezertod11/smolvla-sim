"""Download an explicitly pinned model revision to the external data directory."""

import argparse
import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download

parser = argparse.ArgumentParser()
parser.add_argument("name", choices=["reference", "base"])
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
spec = json.loads((root / "configs/artifacts.json").read_text())[args.name]
data = Path(os.environ.get("ROBOTICS_DATA_DIR", "/data"))
destination = data / "models" / args.name
snapshot_download(**spec, local_dir=destination)
print(destination)
