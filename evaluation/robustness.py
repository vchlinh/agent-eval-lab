"""
Robustness: how consistently the agent solves the SAME task across
repeated trials, expressed as a raw k/N count per task (e.g. 2/3), not
collapsed into a single rate. A task that's 3/3 is reliably solvable; a
task that's 1/3 is solvable but usually isn't -- flattening both to "the
task passes X% of the time" loses exactly the distinction this metric
exists to preserve. See the project's ground rules: trials measure
within-task stochasticity, they are NOT extra independent tasks for
cross-config statistics (that's what pass_rate_by_task in correctness.py
is for).
"""

from __future__ import annotations


def robustness_by_task(results: list[dict]) -> dict[str, dict]:
    """
    Per task: {"passed": k, "trials": N, "fraction": k/N}, e.g.
    {"task_004": {"passed": 2, "trials": 3, "fraction": 0.667}, ...}
    """
    by_task: dict[str, list[bool]] = {}
    for r in results:
        by_task.setdefault(r["task_id"], []).append(r["passed"])

    return {
        task: {
            "passed": sum(v),
            "trials": len(v),
            "fraction": sum(v) / len(v),
        }
        for task, v in by_task.items()
    }


def robustness_histogram(results: list[dict]) -> dict[str, int]:
    """
    How many tasks fall into each k/N bucket (e.g. "0/3": 4, "1/3": 2,
    "3/3": 11) -- a quick shape-of-robustness summary across the whole
    benchmark. Buckets are labeled by each task's own trial count, so a
    mixed-trial-count run (some tasks run 2x, others 3x) still produces
    sensible labels rather than forcing everything onto one denominator.
    """
    per_task = robustness_by_task(results)
    histogram: dict[str, int] = {}
    for stats in per_task.values():
        label = f"{stats['passed']}/{stats['trials']}"
        histogram[label] = histogram.get(label, 0) + 1
    return histogram
