"""Inspect pinned metadata only; never download demonstrations or model weights.

Run in the project's existing Python environment. Raw metadata stays in memory.
The optional JSON output is a reproducible episode selection, not a training run.
"""

import argparse
import ast
import hashlib
import io
import json
import urllib.request
from importlib.metadata import distribution
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import HfApi

PROJECT = Path(__file__).resolve().parents[1]


def read_metadata(url, evidence):
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read(2_000_001)
    if len(content) > 2_000_000:
        raise ValueError(f"Unexpectedly large metadata: {url}")
    evidence.append({
        "url": url, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
    })
    return content


def inspect():
    artifacts = json.loads((PROJECT / "configs/artifacts.json").read_text())
    dataset = artifacts["dataset"]
    base = artifacts["base"]
    root = f"https://huggingface.co/datasets/{dataset['repo_id']}/resolve/{dataset['revision']}"
    evidence = []
    info = json.loads(read_metadata(f"{root}/meta/info.json", evidence))
    tasks = pq.read_table(io.BytesIO(read_metadata(
        f"{root}/meta/tasks.parquet", evidence
    ))).to_pandas()
    # This pinned revision has one metadata shard. Count checks below reject an
    # incomplete selection if a future artifact revision changes the layout.
    episodes = pq.read_table(io.BytesIO(read_metadata(
        f"{root}/meta/episodes/chunk-000/file-000.parquet", evidence
    ))).to_pylist()
    base_config = json.loads(read_metadata(
        f"https://huggingface.co/{base['repo_id']}/resolve/{base['revision']}/config.json",
        evidence,
    ))
    if len(episodes) != info["total_episodes"] or len(tasks) != info["total_tasks"]:
        raise ValueError("Incomplete metadata")
    if sum(ep["length"] for ep in episodes) != info["total_frames"]:
        raise ValueError("Frame count mismatch")
    if len({ep["episode_index"] for ep in episodes}) != len(episodes):
        raise ValueError("Duplicate episode indices")

    # Read literals without importing LIBERO: importing it can prompt for setup.
    task_map_path = distribution("hf-libero").locate_file(
        "libero/libero/benchmark/libero_suite_task_map.py"
    )
    tree = ast.parse(task_map_path.read_text())
    task_map = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "libero_task_map"
                            for t in node.targets))
    names = [name.replace("_", " ") for name in task_map["libero_object"]]
    if len(names) != 10 or not set(names).issubset(tasks.index):
        raise ValueError("LIBERO task names do not match dataset metadata")
    if any(len(ep["tasks"]) != 1 for ep in episodes):
        raise ValueError("Expected one task per demonstration")
    selected = [ep for ep in episodes if ep["tasks"][0] in names]
    by_task = []
    for suite_index, name in enumerate(names):
        group = [ep for ep in selected if ep["tasks"][0] == name]
        if not group:
            raise ValueError(f"No episodes for {name}")
        by_task.append({
            "suite_task_id_order_0": suite_index,
            "dataset_task_index": int(tasks.loc[name, "task_index"]),
            "instruction": name, "episodes": len(group),
            "frames": sum(ep["length"] for ep in group),
        })

    files = {f.path: f.size for f in HfApi().list_repo_tree(
        dataset["repo_id"], repo_type="dataset", revision=dataset["revision"],
        path_in_repo="data", recursive=True,
    ) if hasattr(f, "size")}
    paths = sorted({info["data_path"].format(
        chunk_index=ep["data/chunk_index"], file_index=ep["data/file_index"]
    ) for ep in selected})
    if any(feature["dtype"] == "video" for feature in info["features"].values()):
        raise ValueError("Video files require a separate size calculation")
    return {
        "dataset": dataset, "base": base,
        "installed_lerobot": json.loads(distribution("lerobot").read_text("direct_url.json")),
        "installed_hf_libero": distribution("hf-libero").version,
        "suite_task_map_sha256": hashlib.sha256(task_map_path.read_bytes()).hexdigest(),
        "sources": evidence,
        "dataset_summary": {key: info[key] for key in (
            "codebase_version", "robot_type", "fps", "total_tasks", "total_episodes",
            "total_frames", "features",
        )},
        "base_input_features": base_config["input_features"],
        "base_output_features": base_config["output_features"],
        "rename_map": {
            "observation.images.image": "observation.images.camera1",
            "observation.images.image2": "observation.images.camera2",
        },
        "selection": {
            "suite": "libero_object", "tasks": by_task,
            "episode_indices": sorted(ep["episode_index"] for ep in selected),
            "total_episodes": len(selected),
            "total_frames": sum(ep["length"] for ep in selected),
            "data_files": paths,
            "download_bytes": sum(files[path] for path in paths),
            "full_dataset_data_bytes": sum(files.values()),
            "size_note": "Parquet download sizes only; excludes caches, weights and outputs."
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Save the selection manifest as JSON")
    args = parser.parse_args()
    report = inspect()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    selected = report["selection"]
    print(json.dumps({key: selected[key] for key in (
        "suite", "total_episodes", "total_frames", "download_bytes", "full_dataset_data_bytes",
    )}, indent=2))
    print(f"Selected data files: {len(selected['data_files'])}")


if __name__ == "__main__":
    main()
