"""Inspect physical episode IDs before constructing the image dataset."""

import json
import os
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "configs/libero_object_episodes.json").read_text())
data = Path(os.environ["ROBOTICS_DATA_DIR"]) / "datasets/libero_object"
counts = Counter()
for relative in manifest["selection"]["data_files"]:
    rows = pq.read_table(data / relative, columns=["episode_index", "task_index"]).to_pydict()
    counts.update(rows["episode_index"])
    print(relative, "episodes", min(rows["episode_index"]), max(rows["episode_index"]),
          "tasks", sorted(set(rows["task_index"])), flush=True)
selected = manifest["selection"]["episode_indices"]
print("Selected IDs present:", len(set(selected) & counts.keys()),
      "selected frames:", sum(counts[x] for x in selected), flush=True)
if not set(selected).issubset(counts):
    raise SystemExit("Physical files do not contain all selected metadata episodes")
if sum(counts[x] for x in selected) != manifest["selection"]["total_frames"]:
    raise SystemExit("Physical frame count differs from metadata")
