import json

from scripts.summarize_evaluations import load_run


def test_load_run_validates_and_combines_protocol(tmp_path):
    report = {
        "per_task": [
            {"task_group": "libero_object", "task_id": task,
             "metrics": {"successes": [True] * 10}}
            for task in range(10)
        ],
        "overall": {"n_episodes": 100, "pc_success": 100.0, "eval_ep_s": 2.5},
    }
    protocol = {"precision": "bf16", "n_action_steps": 10}
    (tmp_path / "eval_info.json").write_text(json.dumps(report))
    (tmp_path / "protocol.json").write_text(json.dumps(protocol))

    result = load_run(f"own={tmp_path}")

    assert result["label"] == "own"
    assert result["successes"] == 100
    assert result["mean_episode_seconds"] == 2.5
