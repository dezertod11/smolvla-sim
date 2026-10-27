from smolvla_service.snapshots import fresh_synchronized_snapshot


def test_snapshot_requires_all_inputs_from_one_time_window():
    inputs = {
        "camera": ("camera-new", 10.00),
        "wrist": ("wrist-old", 9.89),
        "state": ("state-new", 10.01),
    }
    bundle, snapshot = fresh_synchronized_snapshot(
        inputs, now=10.02, timeout_s=2.0, tolerance_s=0.08
    )
    assert bundle is None
    assert snapshot is None


def test_snapshot_returns_matching_payloads_and_source_entries():
    inputs = {
        "camera": ("camera", 10.00),
        "wrist": ("wrist", 10.01),
        "state": ("state", 10.02),
    }
    bundle, snapshot = fresh_synchronized_snapshot(
        inputs, now=10.03, timeout_s=2.0, tolerance_s=0.08
    )
    assert bundle == ("camera", "wrist", "state")
    assert snapshot == inputs


def test_snapshot_rejects_stale_inputs():
    inputs = {
        "camera": ("camera", 7.00),
        "wrist": ("wrist", 7.01),
        "state": ("state", 7.02),
    }
    bundle, snapshot = fresh_synchronized_snapshot(
        inputs, now=10.00, timeout_s=2.0, tolerance_s=0.08
    )
    assert bundle is None
    assert snapshot is None
