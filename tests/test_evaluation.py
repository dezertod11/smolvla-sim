import copy

import pytest

from smolvla_service.evaluation import summarize


def report():
    return {"per_task": [{"task_group": "libero_object", "task_id": i,
                          "metrics": {"successes": [True, False] * 5}} for i in range(10)],
            "overall": {"n_episodes": 100, "pc_success": 50.0}}


def test_complete_report():
    assert summarize(report())["successes"] == 50


@pytest.mark.parametrize("change", ["missing_task", "missing_episode", "bad_aggregate"])
def test_incomplete_or_inconsistent_report_rejected(change):
    data = copy.deepcopy(report())
    if change == "missing_task":
        data["per_task"].pop()
    elif change == "missing_episode":
        data["per_task"][0]["metrics"]["successes"].pop()
    else:
        data["overall"]["pc_success"] = 100
    with pytest.raises(ValueError):
        summarize(data)
