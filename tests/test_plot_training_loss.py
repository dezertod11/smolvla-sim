import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "plot_training_loss.py"
SPEC = importlib.util.spec_from_file_location("plot_training_loss", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_metrics_uses_log_frequency_for_exact_steps():
    text = """
INFO 2026-10-12 03:00:00 train.py:1 step:0K loss:0.321 grdn:1.25 lr:1e-05
progress noise\rINFO 2026-10-12 03:00:10 train.py:1 step:0K loss:0.210 grdn:0.80 lr:2e-05
"""

    assert MODULE.parse_metrics(text, 50) == [
        {"step": 50, "loss": 0.321, "grad_norm": 1.25, "learning_rate": 1e-05},
        {"step": 100, "loss": 0.210, "grad_norm": 0.80, "learning_rate": 2e-05},
    ]
