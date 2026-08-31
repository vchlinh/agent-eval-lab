"""
Runs the Day-3 curated judge sample: a small, hand-picked set of real
patches from the Config A vs Config B experiment, scored by
evaluation/judge.py, plus the two built-in stress cases. This is
deliberately NOT run over every trial -- see the project's ground rules
on the judge only ever running on a curated sample.

    python -m evaluation.run_judge_sample

Writes results/judge_sample_<timestamp>/report.json and prints a summary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent.providers import OllamaProvider
from benchmark.schema import load_task
from evaluation.judge import (
    built_in_stress_cases,
    compare_patches_blind,
    extract_final_diff,
    judge_patch_repeated,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = PROJECT_ROOT / "benchmark" / "tasks"
RUN_A = PROJECT_ROOT / "results" / "run_20260828T165716Z_qwen2.5-coder-7b"
RUN_B = PROJECT_ROOT / "results" / "run_20260831T024931Z_qwen2.5-coder-7b_contextB"
JUDGE_MODEL = "qwen2.5-coder:7b"

# Head-to-head pairs: one task per category where BOTH configs passed the
# chosen trial, picked to span as many of the benchmark's six categories
# as budget allows (5 tasks x 2 configs = 10 patches, matching the plan's
# "~10 representative patches").
HEAD_TO_HEAD = [
    ("task_001", 1),  # bug_fix
    ("task_002", 1),  # feature
    ("task_003", 1),  # edge_case
    ("task_008", 2),  # refactor
    ("task_009", 1),  # api_change_docs
]

# One standalone case: test_writing had a 0% -> 83% flip under Context B
# (all 3 test_writing tasks), the single most dramatic category result in
# the whole experiment. There's no Config A patch to pair it against here
# (A never produced a passing solution for this task), so this checks
# Config B's new fix on its own merits rather than head-to-head.
STANDALONE = [("task_016", "B", 1)]


def _trace_path(run_dir: Path, task_id: str, trial: int) -> Path:
    return run_dir / "traces" / f"{task_id}_trial{trial}.jsonl"


def main() -> None:
    provider = OllamaProvider(model=JUDGE_MODEL, temperature=0.2)
    report: dict = {"model": JUDGE_MODEL, "head_to_head": [], "standalone": [], "stress_cases": []}

    print("=== Stress cases ===", flush=True)
    for case in built_in_stress_cases(TASKS_ROOT):
        print(f"  judging {case['label']} ...", flush=True)
        result = judge_patch_repeated(case["task_description"], case["diff_text"], provider, n=3)
        report["stress_cases"].append({"label": case["label"], "task_id": case["task_id"], **result})
        means = {d: round(result[d]["mean"], 2) for d in ("readability", "minimality", "root_cause_vs_patch")}
        print(f"    means: {means}")

    print("\n=== Head-to-head (Config A vs Config B, same task) ===", flush=True)
    for task_id, trial in HEAD_TO_HEAD:
        task = load_task(TASKS_ROOT / task_id)
        diff_a = extract_final_diff(task, _trace_path(RUN_A, task_id, trial))
        diff_b = extract_final_diff(task, _trace_path(RUN_B, task_id, trial))

        print(f"  {task_id} ({task.category.value}) trial {trial} ...", flush=True)
        rubric_a = judge_patch_repeated(task.description, diff_a, provider, n=2)
        rubric_b = judge_patch_repeated(task.description, diff_b, provider, n=2)
        comparison = compare_patches_blind(task.description, diff_a, diff_b, provider, seed=hash(task_id) & 0xFFFF)

        entry = {
            "task_id": task_id,
            "category": task.category.value,
            "trial": trial,
            "rubric_a": {d: round(rubric_a[d]["mean"], 2) for d in ("readability", "minimality", "root_cause_vs_patch")},
            "rubric_b": {d: round(rubric_b[d]["mean"], 2) for d in ("readability", "minimality", "root_cause_vs_patch")},
            "blind_comparison": comparison,
        }
        report["head_to_head"].append(entry)
        print(f"    A rubric: {entry['rubric_a']}  B rubric: {entry['rubric_b']}")
        print(f"    blind preference: {comparison['preferred_config']} -- {comparison['rationale']}")

    print("\n=== Standalone (no passing counterpart in the other config) ===", flush=True)
    for task_id, config, trial in STANDALONE:
        task = load_task(TASKS_ROOT / task_id)
        run_dir = RUN_A if config == "A" else RUN_B
        diff_text = extract_final_diff(task, _trace_path(run_dir, task_id, trial))

        print(f"  {task_id} ({task.category.value}) config {config} trial {trial} ...", flush=True)
        rubric = judge_patch_repeated(task.description, diff_text, provider, n=3)
        entry = {
            "task_id": task_id,
            "category": task.category.value,
            "config": config,
            "trial": trial,
            "rubric": {d: round(rubric[d]["mean"], 2) for d in ("readability", "minimality", "root_cause_vs_patch")},
        }
        report["standalone"].append(entry)
        print(f"    rubric: {entry['rubric']}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = PROJECT_ROOT / "results" / f"judge_sample_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    print(f"\nwrote {out_dir / 'report.json'}")


if __name__ == "__main__":
    main()
