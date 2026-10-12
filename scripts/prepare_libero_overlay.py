"""Build a verified local LIBERO metadata overlay for selected episodes.

The pinned upstream revision has stale ``data/file_index`` values in
``meta/episodes`` after its Parquet files were repartitioned.  Keep the downloaded
dataset immutable and create a small overlay whose metadata points at the audited
physical files.
"""

import hashlib
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def file_index(path):
    return int(Path(path).stem.removeprefix("file-"))


def main():
    project = Path(__file__).resolve().parents[1]
    runtime = Path(os.environ["ROBOTICS_DATA_DIR"])
    source = runtime / "datasets/libero"
    target = runtime / "datasets/libero_object"
    selection = json.loads((project / "configs/libero_object_episodes.json").read_text())[
        "selection"
    ]
    selected = set(selection["episode_indices"])
    physical = {}
    counts = defaultdict(int)
    tasks = defaultdict(set)
    indices = defaultdict(list)

    for relative in selection["data_files"]:
        table = pq.read_table(
            source / relative,
            columns=["episode_index", "task_index", "index"],
            filters=pc.field("episode_index").isin(selected),
        )
        payload = table.to_pydict()
        for episode, task, index in zip(
            payload["episode_index"], payload["task_index"], payload["index"], strict=True
        ):
            if episode in physical and physical[episode] != relative:
                raise ValueError(f"Episode {episode} occurs in multiple files")
            physical[episode] = relative
            counts[episode] += 1
            tasks[episode].add(task)
            indices[episode].append(index)

    missing = selected - physical.keys()
    if missing:
        raise ValueError(f"Missing selected episodes: {sorted(missing)[:10]}")

    episode_file = source / "meta/episodes/chunk-000/file-000.parquet"
    metadata = pq.read_table(episode_file)
    rows = metadata.to_pylist()
    task_rows = pq.read_table(source / "meta/tasks.parquet").to_pylist()
    task_names = {row["task_index"]: row["task"] for row in task_rows}
    verified_frames = 0
    for row in rows:
        episode = row["episode_index"]
        if episode not in selected:
            continue
        relative = physical[episode]
        expected_task = {task_names[index] for index in tasks[episode]}
        if counts[episode] != row["length"]:
            raise ValueError(f"Length mismatch for episode {episode}")
        if set(row["tasks"]) != expected_task:
            raise ValueError(f"Task mismatch for episode {episode}")
        if min(indices[episode]) != row["dataset_from_index"]:
            raise ValueError(f"Start index mismatch for episode {episode}")
        if max(indices[episode]) + 1 != row["dataset_to_index"]:
            raise ValueError(f"End index mismatch for episode {episode}")
        row["data/chunk_index"] = 0
        row["data/file_index"] = file_index(relative)
        verified_frames += counts[episode]
    if verified_frames != selection["total_frames"]:
        raise ValueError("Selected frame count differs from the pinned manifest")

    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing overlay: {target}")
    (target / "meta/episodes/chunk-000").mkdir(parents=True)
    (target / "data/chunk-000").mkdir(parents=True)
    for name in ["info.json", "stats.json", "tasks.parquet"]:
        shutil.copy2(source / "meta" / name, target / "meta" / name)
    repaired = pa.Table.from_pylist(rows, schema=metadata.schema)
    repaired_path = target / "meta/episodes/chunk-000/file-000.parquet"
    pq.write_table(repaired, repaired_path)
    for relative in selection["data_files"]:
        source_file = (source / relative).resolve()
        link = target / relative
        link.symlink_to(source_file)

    evidence = {
        "source_episode_metadata_sha256": hashlib.sha256(episode_file.read_bytes()).hexdigest(),
        "repaired_episode_metadata_sha256": hashlib.sha256(repaired_path.read_bytes()).hexdigest(),
        "episodes": len(selected),
        "frames": verified_frames,
        "physical_files": len(selection["data_files"]),
    }
    (target / "overlay.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
