"""Prepare this project's LIBERO paths without an interactive import prompt."""

import importlib.metadata
import os
from pathlib import Path

import yaml


def configure():
    root = Path(importlib.metadata.distribution("hf-libero").locate_file("libero/libero"))
    config_dir = Path(os.environ["LIBERO_CONFIG_PATH"])
    data_dir = Path(os.environ.get("ROBOTICS_DATA_DIR", "/data"))
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "benchmark_root": str(root),
        "bddl_files": str(root / "bddl_files"),
        "init_states": str(root / "init_files"),
        "datasets": str(data_dir / "datasets"),
        "assets": str(root / "assets"),
    }
    (config_dir / "config.yaml").write_text(yaml.safe_dump(config))


if __name__ == "__main__":
    configure()
