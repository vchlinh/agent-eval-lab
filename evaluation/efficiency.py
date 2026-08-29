"""
Efficiency: how much it cost the agent to reach its result, independent
of whether it passed -- tool calls, iterations, wall-clock time, tokens,
and an estimated dollar cost. A run that passes in 3 iterations and one
that passes in 15 are not equally good, even though harness/runner.py
records both as PASS.

Local Ollama inference is actually free, but the plan calls for reasoning
about cost as a metric even at $0 real spend. COST_PER_1M_*_TOKENS below
use Claude Haiku 4.5's published per-token rates ($1.00 / $5.00 per 1M
tokens as of this project's Day 2 -- a small, cheap model roughly
comparable in class to what's being evaluated here) purely as an
illustrative reference point for "what would this have cost on a real
hosted API," not a claim about actual spend.
"""

from __future__ import annotations

import statistics

COST_PER_1M_INPUT_TOKENS = 1.00
COST_PER_1M_OUTPUT_TOKENS = 5.00


def estimated_cost_usd(tokens_in: int, tokens_out: int) -> float:
    return (
        tokens_in / 1_000_000 * COST_PER_1M_INPUT_TOKENS
        + tokens_out / 1_000_000 * COST_PER_1M_OUTPUT_TOKENS
    )


def tidy_table(results: list[dict]) -> list[dict]:
    """
    The Day 2 checkpoint shape: one row per (task_id, trial) with
    task_id, trial, category, passed, iterations, tool_calls, latency,
    est_cost. `latency_seconds` is wall-clock time for the whole trial
    (agent loop + grading) -- the number that actually matters for "how
    long did this take" -- not the sum of individual provider round-trip
    latencies (still available per-row in results.json as
    total_latency_ms, if that's ever needed instead).
    """
    rows = []
    for r in results:
        rows.append({
            "task_id": r["task_id"],
            "trial": r["trial"],
            "category": r["category"],
            "passed": r["passed"],
            "iterations": r["iterations"],
            "tool_calls": r["tool_calls"],
            "latency_seconds": round(r["wall_clock_seconds"], 1),
            "est_cost_usd": round(estimated_cost_usd(r["tokens_in"], r["tokens_out"]), 6),
        })
    return rows


def _mean_median(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "median": 0.0}
    return {"mean": statistics.mean(values), "median": statistics.median(values)}


def efficiency_summary(results: list[dict]) -> dict:
    """
    Mean/median for each efficiency metric across every trial in
    `results`. Median matters as much as mean here -- a handful of
    stuck-loop trials (several hit the full iteration budget during this
    project's live checks) can drag the mean far from what a "typical"
    run actually looks like.
    """
    if not results:
        return {}
    return {
        "iterations": _mean_median([r["iterations"] for r in results]),
        "tool_calls": _mean_median([r["tool_calls"] for r in results]),
        "wall_clock_seconds": _mean_median([r["wall_clock_seconds"] for r in results]),
        "tokens_in": _mean_median([r["tokens_in"] for r in results]),
        "tokens_out": _mean_median([r["tokens_out"] for r in results]),
        "est_cost_usd": _mean_median(
            [estimated_cost_usd(r["tokens_in"], r["tokens_out"]) for r in results]
        ),
        "n_trials": len(results),
    }


def efficiency_summary_by_category(results: list[dict]) -> dict[str, dict]:
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)
    return {cat: efficiency_summary(rows) for cat, rows in by_cat.items()}
