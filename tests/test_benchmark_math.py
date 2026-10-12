import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from benchmark_policy import percentile


def test_percentile_interpolates_sorted_samples():
    assert percentile([40, 10, 30, 20], 0.5) == 25
    assert percentile([0, 10, 20], 0.95) == 19
