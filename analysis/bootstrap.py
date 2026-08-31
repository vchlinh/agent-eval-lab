"""
Paired bootstrap on the task-level success-rate difference between two
configs (Config B minus Config A).

Why "paired" and why resample TASKS, not trials: the ~20 tasks are the
real experimental unit for comparing configs (see the project's ground
rules -- 20 tasks x N trials is not N*20 independent data points). Some
tasks are just harder than others regardless of context strategy, so a
fair resample has to keep each task's Config-A-outcome and
Config-B-outcome glued together and resample task *indices* with
replacement -- resampling trials independently would let a resample
compare a hard task's A-outcome against an easy task's B-outcome, which
answers a different, wrong question.

No numpy/scipy dependency, in keeping with this project's stdlib-only
footprint elsewhere: resampling with Python's own `random` module is
plenty fast at n_resamples in the thousands over ~20 tasks.
"""

from __future__ import annotations

import random


def paired_bootstrap_diff(
    task_rates_a: dict[str, float],
    task_rates_b: dict[str, float],
    n_resamples: int = 10000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    task_rates_a / task_rates_b: {task_id: fraction of trials passed} --
    e.g. from evaluation.correctness.pass_rate_by_task(). Must cover the
    same set of task ids (both configs ran the same benchmark), or this
    raises rather than silently comparing mismatched tasks.

    Returns {n_tasks, observed_diff, ci_lower, ci_upper, confidence,
    n_resamples}. observed_diff and the CI are both mean(B) - mean(A)
    across tasks; a CI that excludes 0 is the bootstrap's way of saying
    "the direction of this difference is unlikely to be noise."
    """
    tasks_a, tasks_b = set(task_rates_a), set(task_rates_b)
    if tasks_a != tasks_b:
        raise ValueError(
            "task sets don't match between configs: "
            f"only in A={tasks_a - tasks_b or None}, only in B={tasks_b - tasks_a or None}"
        )
    if not 0 < confidence < 1:
        raise ValueError(f"confidence must be in (0, 1), got {confidence!r}")

    tasks = sorted(tasks_a)
    n = len(tasks)
    a_vals = [task_rates_a[t] for t in tasks]
    b_vals = [task_rates_b[t] for t in tasks]

    observed_diff = sum(b_vals) / n - sum(a_vals) / n

    rng = random.Random(seed)
    indices = range(n)
    diffs = []
    for _ in range(n_resamples):
        sample = rng.choices(indices, k=n)
        a_mean = sum(a_vals[i] for i in sample) / n
        b_mean = sum(b_vals[i] for i in sample) / n
        diffs.append(b_mean - a_mean)

    diffs.sort()
    lo_pct = (1 - confidence) / 2
    hi_pct = 1 - lo_pct
    lower = diffs[int(lo_pct * n_resamples)]
    upper = diffs[min(n_resamples - 1, int(hi_pct * n_resamples))]

    return {
        "n_tasks": n,
        "observed_diff": observed_diff,
        "ci_lower": lower,
        "ci_upper": upper,
        "confidence": confidence,
        "n_resamples": n_resamples,
    }


def bootstrap_median_ci(
    values: list[float],
    n_resamples: int = 10000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    Single-sample bootstrap CI on the median of `values` (e.g. one config's
    per-trial iteration counts or latencies). Separate from the paired
    diff above -- this describes one config's own typical value with
    uncertainty, not a cross-config comparison. Median rather than mean
    matters here specifically because several trials in this project hit
    the full iteration budget and would drag a mean-based CI around.
    """
    n = len(values)
    if n == 0:
        raise ValueError("cannot bootstrap an empty sample")
    if not 0 < confidence < 1:
        raise ValueError(f"confidence must be in (0, 1), got {confidence!r}")

    observed_median = _median(values)

    rng = random.Random(seed)
    indices = range(n)
    medians = []
    for _ in range(n_resamples):
        sample = [values[i] for i in rng.choices(indices, k=n)]
        medians.append(_median(sample))

    medians.sort()
    lo_pct = (1 - confidence) / 2
    hi_pct = 1 - lo_pct
    lower = medians[int(lo_pct * n_resamples)]
    upper = medians[min(n_resamples - 1, int(hi_pct * n_resamples))]

    return {
        "n": n,
        "observed_median": observed_median,
        "ci_lower": lower,
        "ci_upper": upper,
        "confidence": confidence,
        "n_resamples": n_resamples,
    }


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
