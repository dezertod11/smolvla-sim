from pathlib import Path

import pytest
import yaml

from smolvla_service.ros_config import load_policy_parameters


ROOT = Path(__file__).parents[1]


def test_final_ros_config_loads_required_runtime_parameters():
    parameters = load_policy_parameters(
        ROOT / "ros2_ws/src/vla_bridge/config/libero_object_own_final.yaml"
    )
    assert parameters["checkpoint"] == "/data/models/own-final"
    assert parameters["precision"] == "bf16"
    assert parameters["n_action_steps"] == 10


def test_ros_config_rejects_unknown_precision(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "smolvla": {
                    "ros__parameters": {
                        "checkpoint": "/model",
                        "vlm_model": "/vlm",
                        "task": "test",
                        "device": "cuda",
                        "precision": "fp4",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unsupported precision"):
        load_policy_parameters(path)
