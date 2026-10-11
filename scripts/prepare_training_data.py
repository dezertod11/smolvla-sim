"""Download only pinned models and the selected LIBERO shards, without a GPU."""

import hashlib
import json
import os
import shutil
from pathlib import Path

from huggingface_hub import snapshot_download


def main():
    project = Path(__file__).resolve().parents[1]
    data = Path(os.environ["ROBOTICS_DATA_DIR"])
    if shutil.disk_usage(data).free < 30 * 1024**3:
        raise SystemExit("At least 30 GiB free is required for data preparation")
    artifacts = json.loads((project / "configs/artifacts.json").read_text())
    selection = json.loads((project / "configs/libero_object_episodes.json").read_text())
    manifest = {"artifacts": artifacts, "files": {}}
    for name in ["base", "vlm", "reference"]:
        dest = data / "models" / name
        print(f"Downloading pinned {name} -> {dest}", flush=True)
        snapshot_download(**artifacts[name], local_dir=dest,
                          ignore_patterns=["*.onnx", "*.tflite", "*.h5", "*.msgpack"],
                          max_workers=4)
        for p in dest.rglob("*"):
            if p.is_file() and ".cache" not in p.parts:
                with p.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                manifest["files"][str(p.relative_to(data))] = digest
    dest = data / "datasets/libero"
    print("Downloading LIBERO metadata and 19 selected Parquet shards", flush=True)
    snapshot_download(**artifacts["dataset"], repo_type="dataset", local_dir=dest,
                      allow_patterns=["meta/**", *selection["selection"]["data_files"]],
                      max_workers=4)
    for relative in selection["selection"]["data_files"]:
        p = dest / relative
        with p.open("rb") as handle:
            manifest["files"][str(p.relative_to(data))] = hashlib.file_digest(
                handle, "sha256"
            ).hexdigest()
    out = data / "prepared_artifacts.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared and hashed {len(manifest['files'])} files; manifest: {out}", flush=True)


if __name__ == "__main__":
    main()
