import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "control", Path(__file__).parents[1] / "scripts/control.py"
)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.mark.parametrize("payload", [
    {"backend": "h100", "action": "logs", "value": "; rm -rf /"},
    {"backend": "h100", "action": "submit", "value": "../../outside.json"},
    {"backend": "pc1", "action": "shell", "value": "echo hello"},
    {"backend": "evil", "action": "status"},
])
def test_reject_unsafe_dispatch(payload):
    with pytest.raises(ValueError):
        control.command(payload)


def test_status_is_fixed_argv():
    assert control.command({"backend": "h100", "action": "status"}) == [
        "bash", "scripts/experiment.sh", "h100", "status",
    ]
