"""
McNemar's test on the paired task-level pass/fail 2x2 table between two
configs.

Why McNemar and not a plain two-sample proportion test: the same 20 tasks
were run under both configs, so the two pass/fail rates aren't independent
samples -- they're paired. McNemar's test is built exactly for "paired
before/after (or A/B) binary outcomes": it ignores the tasks both configs
agree on (both pass, both fail) entirely and asks only whether the
*disagreements* are lopsided in one direction. If Config B fixes 8 tasks
that Config A failed, and Config A fixes only 1 task that Config B
failed, that 8-vs-1 split among the disagreements is what the test
actually evaluates -- not the raw 75% vs 45% headline rate.

Exact binomial form, no scipy/statsmodels: with only ~20 tasks the
discordant-pair count is small, where the exact test (not the chi-square
approximation) is the correct one to use anyway -- statsmodels itself
defaults to exact when n < 25. The exact two-sided p-value under
McNemar's null (each discordant pair is a fair coin flip between "A right,
B wrong" and "B right, A wrong") has a closed form using the binomial
distribution, computed here with math.comb rather than importing scipy
for one distribution.
"""

from __future__ import annotations

import math


def binarize_task_pass(task_rates: dict[str, float], pass_threshold: float = 0.5) -> dict[str, bool]:
    """
    Collapses each task's per-trial success fraction (e.g. 0.5 for 1-of-2
    trials passed) into a single pass/fail verdict for the paired table
    below. Default threshold counts a tie (exactly half the trials
    passing) as a pass -- with only 2 trials/task in this project, that
    makes "solved at least once" the practical definition, matching how
    the robustness histogram already treats 1/2 as a distinct, partially-
    successful bucket rather than lumping it in with 0/2.
    """
    return {task: rate >= pass_threshold for task, rate in task_rates.items()}


def contingency_table(task_pass_a: dict[str, bool], task_pass_b: dict[str, bool]) -> dict[str, int]:
    """
    The 2x2 table over tasks common to both configs:
      both_pass, both_fail  -- concordant, irrelevant to McNemar
      a_only  -- passed under A, failed under B
      b_only  -- passed under B, failed under A
    """
    tasks_a, tasks_b = set(task_pass_a), set(task_pass_b)
    if tasks_a != tasks_b:
        raise ValueError(
            "task sets don't match between configs: "
            f"only in A={tasks_a - tasks_b or None}, only in B={tasks_b - tasks_a or None}"
        )

    both_pass = a_only = b_only = both_fail = 0
    for task in tasks_a:
        a, b = task_pass_a[task], task_pass_b[task]
        if a and b:
            both_pass += 1
        elif a and not b:
            a_only += 1
        elif b and not a:
            b_only += 1
        else:
            both_fail += 1

    return {"both_pass": both_pass, "a_only": a_only, "b_only": b_only, "both_fail": both_fail}


def _binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1))


def mcnemar_exact_pvalue(a_only: int, b_only: int) -> float:
    """
    Two-sided exact McNemar p-value from the two discordant counts. Under
    the null, each discordant task is an independent fair coin flip
    between "A_only" and "B_only", so their total n = a_only + b_only is
    Binomial(n, 0.5) -- symmetric, which is what lets the two-sided
    p-value collapse to 2 * P(X <= min(a_only, b_only)), capped at 1.
    """
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    return min(1.0, 2 * _binom_cdf(k, n))


def mcnemar_test(
    task_rates_a: dict[str, float],
    task_rates_b: dict[str, float],
    pass_threshold: float = 0.5,
) -> dict:
    """
    Full McNemar test from two configs' per-task success-rate dicts (e.g.
    from evaluation.correctness.pass_rate_by_task()). Binarizes each task
    per binarize_task_pass(), builds the contingency table, and returns
    the table plus the exact two-sided p-value.
    """
    task_pass_a = binarize_task_pass(task_rates_a, pass_threshold)
    task_pass_b = binarize_task_pass(task_rates_b, pass_threshold)
    table = contingency_table(task_pass_a, task_pass_b)
    p_value = mcnemar_exact_pvalue(table["a_only"], table["b_only"])
    return {**table, "p_value": p_value}
