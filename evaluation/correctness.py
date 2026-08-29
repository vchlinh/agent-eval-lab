"""
Correctness: pass/fail against hidden tests, aggregated across trials,
tasks, and categories. Ground truth is always what harness/runner.py's
`Sandbox.run_hidden_tests()` reported for that trial (the `passed` field
in results.json) -- never anything self-reported by the agent, and never
the LLM judge (evaluation/judge.py scores quality on a curated sample; it
never decides pass/fail -- see the project's ground rules).
"""

from __future__ import annotations

import json
from pathlib import Path


def load_results(run_dir: Path) -> list[dict]:
    """Load one run's results.json (see harness/runner.py) as a flat list
    of per-trial result dicts."""
    return json.loads((Path(run_dir) / "results.json").read_text())


def overall_pass_rate(results: list[dict]) -> float:
    """Fraction of ALL trials (across every task) that passed. This is a
    per-trial rate, not a per-task rate -- a task run 3 times counts 3
    times here. Use pass_rate_by_task() for the per-task view."""
    if not results:
        return 0.0
    return sum(1 for r in results if r["passed"]) / len(results)


def pass_rate_by_category(results: list[dict]) -> dict[str, float]:
    """Per-trial pass rate, grouped by task category."""
    by_cat: dict[str, list[bool]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r["passed"])
    return {cat: sum(v) / len(v) for cat, v in by_cat.items()}


def pass_rate_by_task(results: list[dict]) -> dict[str, float]:
    """
    Fraction of trials that passed, per task -- e.g. task_004: 2/3 trials
    passed -> 0.667. This is the natural unit for cross-config comparison
    (McNemar, paired bootstrap operate over ~20 tasks, not over every
    trial) once analysis/ exists -- see the project's ground rules on why
    trials aren't extra independent tasks.
    """
    by_task: dict[str, list[bool]] = {}
    for r in results:
        by_task.setdefault(r["task_id"], []).append(r["passed"])
    return {task: sum(v) / len(v) for task, v in by_task.items()}
