from dataclasses import dataclass

import numpy as np
import pytest

from smolvla_service.conversion import action_to_list, action_to_message, image_to_chw


def test_rgb_channels_and_scaling():
    image = np.array([[[255, 0, 127], [0, 255, 0]]], dtype=np.uint8)
    result = image_to_chw(image)
    assert result.shape == (3, 1, 2)
    np.testing.assert_allclose(result[:, 0, 0], [1, 0, 127 / 255])
    assert result.flags.c_contiguous


@pytest.mark.parametrize("image", [np.zeros((3, 2, 2)), np.zeros((2, 2, 4), np.uint8)])
def test_reject_invalid_image(image):
    with pytest.raises(ValueError):
        image_to_chw(image)


@pytest.mark.parametrize("action", [[0] * 6, [0] * 8, [float("nan")] * 7])
def test_reject_invalid_action(action):
    with pytest.raises(ValueError):
        action_to_list(action)


def test_action_order_is_preserved():
    assert action_to_list([0, 1, -1, 0.5, -0.5, 0.25, 1]) == [
        0, 1, -1, 0.5, -0.5, 0.25, 1
    ]


def test_action_is_converted_to_ros_compatible_message():
    @dataclass
    class FakeFloat32MultiArray:
        data: list[float]

    message = action_to_message(range(7), FakeFloat32MultiArray)
    assert message.data == [0, 1, 2, 3, 4, 5, 6]
