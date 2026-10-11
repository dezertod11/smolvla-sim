import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
spec = importlib.util.spec_from_file_location("jobs", Path(__file__).parents[1] / "scripts/jobs.py")
jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs)


def job(**kw):
    return {"id": "test", "backend": "h100", "kind": "train", "timeout_seconds": 10,
            "command": ["python", "train.py"], **kw}


def policy(**kw):
    return {"approved": True, "approval_note": "test fixture only",
            "limits": {"h100": {"train": {"max_runs": 2, "max_seconds": 20,
                                          "max_run_seconds": 15, **kw}}}}


def test_unapproved_training_is_denied():
    with pytest.raises(ValueError, match="not been approved"):
        jobs.authorize(job(), {}, [])


def test_failed_runs_still_consume_reservation():
    previous = [{"spec": job(timeout_seconds=15), "status": "failed"}]
    with pytest.raises(ValueError, match="Time budget"):
        jobs.authorize(job(), policy(), previous)


def test_count_and_per_run_limits():
    with pytest.raises(ValueError, match="Run-count"):
        jobs.authorize(job(), policy(max_runs=0), [])
    with pytest.raises(ValueError, match="Per-run"):
        jobs.authorize(job(), policy(max_run_seconds=5), [])


@pytest.mark.parametrize("change", [
    {"id": "../escape"}, {"backend": "other"}, {"timeout_seconds": 0},
    {"command": []}, {"backend": "cpu"}, {"kind": "check", "timeout_seconds": 121},
])
def test_invalid_specs(change):
    with pytest.raises(ValueError):
        jobs.validate(job(**change))


def test_atomic_state_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    jobs.write(p, {"status": "running"})
    jobs.write(p, {"status": "succeeded"})
    assert jobs.read(p) == {"status": "succeeded"}
    assert list(tmp_path.glob("*.tmp")) == []
