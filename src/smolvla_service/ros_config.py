"""Load and validate the portable part of a ROS2 parameter file."""

from pathlib import Path

import yaml

SUPPORTED_PRECISIONS = {"bf16", "int8"}


def load_policy_parameters(path):
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    try:
        parameters = document["smolvla"]["ros__parameters"]
    except (KeyError, TypeError) as error:
        raise ValueError("Missing smolvla.ros__parameters") from error
    required = {"checkpoint", "vlm_model", "task", "device", "precision"}
    missing = sorted(required - parameters.keys())
    if missing:
        raise ValueError(f"Missing policy parameters: {', '.join(missing)}")
    if parameters["precision"] not in SUPPORTED_PRECISIONS:
        raise ValueError(
            f"Unsupported precision {parameters['precision']!r}; "
            f"expected one of {sorted(SUPPORTED_PRECISIONS)}"
        )
    return parameters
