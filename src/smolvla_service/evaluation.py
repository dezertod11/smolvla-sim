"""Validate complete LIBERO evaluation reports without loading models or GPUs."""

import math


def summarize(report, task_ids=None, episodes_per_task=10):
    if task_ids is None:
        task_ids = tuple(range(10))
    tasks = report["per_task"]
    ids = [entry["task_id"] for entry in tasks]
    if sorted(ids) != sorted(task_ids):
        raise ValueError("Missing, duplicate or unexpected tasks")
    results = []
    for entry in sorted(tasks, key=lambda row: row["task_id"]):
        if entry["task_group"] != "libero_object":
            raise ValueError("Unexpected suite")
        successes = entry["metrics"]["successes"]
        if len(successes) != episodes_per_task or any(type(x) is not bool for x in successes):
            raise ValueError("Incomplete episodes or invalid success values")
        results.append({"task_id": entry["task_id"], "episodes": len(successes),
                        "successes": sum(successes), "success_rate": sum(successes)/len(successes)})
    count = len(task_ids) * episodes_per_task
    successes = sum(row["successes"] for row in results)
    if report["overall"]["n_episodes"] != count:
        raise ValueError("Overall episode count disagrees with per-task records")
    if not math.isclose(report["overall"]["pc_success"], successes / count * 100, abs_tol=1e-6):
        raise ValueError("Overall success rate disagrees with raw outcomes")
    return {"episodes": count, "successes": successes, "success_rate": successes / count,
            "tasks": results}
