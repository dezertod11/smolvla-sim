"""Prepare this project's LIBERO paths without an interactive import prompt."""

import importlib.metadata
import os
from pathlib import Path

import yaml


def configure_egl_device():
    """Bridge robosuite's physical-ID check to MuJoCo's logical device index."""
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible:
        return
    physical = visible.split(",", maxsplit=1)[0].strip()
    if not physical.isdigit():
        return

    # robosuite checks that EGL's ID is one of the physical CUDA IDs at import.
    os.environ["MUJOCO_EGL_DEVICE_ID"] = physical
    __import__("robosuite.utils.binding_utils")
    # CUDA exposes that single leased card to MuJoCo as logical device zero.
    os.environ["MUJOCO_EGL_DEVICE_ID"] = "0"


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
    configure_egl_device()


if __name__ == "__main__":
    configure()
