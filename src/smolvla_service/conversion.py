"""Validate RGB observations and LIBERO's seven-component actions."""

import numpy as np


def image_to_chw(image: np.ndarray) -> np.ndarray:
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[-1] != 3:
        raise ValueError("Expected an HWC RGB uint8 image")
    return np.ascontiguousarray(image.transpose(2, 0, 1), dtype=np.float32) / 255.0


def action_to_list(action) -> list[float]:
    values = np.asarray(action, dtype=np.float32)
    if values.shape != (7,) or not np.isfinite(values).all():
        raise ValueError("Expected seven finite LIBERO action values")
    return values.tolist()


def action_to_message(action, message_type):
    """Build a ROS-compatible message without importing ROS in CPU tests."""
    return message_type(data=action_to_list(action))
