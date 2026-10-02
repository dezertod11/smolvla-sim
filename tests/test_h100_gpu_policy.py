import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "h100_run", Path(__file__).resolve().parents[1] / "scripts/h100_run.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_gpu_zero_is_never_selected():
    with pytest.raises(ValueError):
        module.select_gpu([[0, 0, 80000, 0]], "smoke", 0)


def test_training_skips_gpu_one_and_busy_cards():
    assert module.select_gpu(
        [[0, 0, 80000, 0], [1, 0, 80000, 0], [2, 3000, 80000, 90], [3, 0, 80000, 0]],
        "train",
    ) == 3


def test_busy_gpu_is_rejected_even_when_explicitly_requested():
    with pytest.raises(RuntimeError):
        module.select_gpu([[2, 5000, 80000, 0]], "train", 2)
