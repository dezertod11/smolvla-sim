"""Audit pinned Parquet footers; do not assume metadata file indices are correct."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import HfApi, HfFileSystem

root = Path(__file__).resolve().parents[1]
artifact = json.loads((root / "configs/artifacts.json").read_text())["dataset"]
selection = json.loads((root / "configs/libero_object_episodes.json").read_text())["selection"]
files = [f for f in HfApi().list_repo_tree(
    artifact["repo_id"], repo_type="dataset", revision=artifact["revision"],
    path_in_repo="data", recursive=True,
) if hasattr(f, "size") and f.path.endswith(".parquet")]
print("Auditing", len(files), "physical files", flush=True)
fs = HfFileSystem()


def inspect(entry):
    path = f"datasets/{artifact['repo_id']}@{artifact['revision']}/{entry.path}"
    with fs.open(path, "rb", block_size=65536) as handle:
        meta = pq.read_metadata(handle)
    groups = []
    for i in range(meta.num_row_groups):
        group = meta.row_group(i)
        stats = {}
        for j in range(group.num_columns):
            column = group.column(j)
            if column.path_in_schema in {"episode_index", "task_index", "index"}:
                s = column.statistics
                stats[column.path_in_schema] = [s.min, s.max] if s and s.has_min_max else None
        groups.append(stats)
    result = {"path": entry.path, "bytes": entry.size, "rows": meta.num_rows, "groups": groups}
    print(entry.path, meta.num_rows, groups[0].get("episode_index"), flush=True)
    return result


with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(inspect, files))
selected = set(selection["episode_indices"])
needed = [r for r in results if any(
    g.get("episode_index") is None or any(g["episode_index"][0] <= x <= g["episode_index"][1]
                                         for x in selected) for g in r["groups"])]
out = Path(os.environ["ROBOTICS_DATA_DIR"]) / "dataset_layout_audit.json"
report = {"artifact": artifact, "files": results, "selected_files": needed}
out.write_text(json.dumps(report, indent=2))
print("Selected physical files", len(needed), "bytes", sum(r["bytes"] for r in needed),
      "total physical rows", sum(r["rows"] for r in results), "report", out, flush=True)
