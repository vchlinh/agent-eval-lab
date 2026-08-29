"""
Runner: orchestrates task -> sandbox -> agent -> hidden-test grading ->
results. This is the top-level entry point:

    python -m harness.runner --task task_001
    python -m harness.runner --task task_001 --trials 3
    python -m harness.runner                      # every QA'd task

Every invocation writes a self-contained results/run_<timestamp>_<model>/
folder: config.json (everything needed to reproduce the run), traces/
(one JSONL file per task/trial), and results.json (the outcome table).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from agent.providers import OllamaProvider
from agent.react_agent import PROMPT_VERSION, run_agent
from benchmark.schema import Task, load_task, load_tasks
from harness.sandbox import Sandbox
from harness.tracer import write_trace

DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TEMPERATURE = 0.2
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = PROJECT_ROOT / "benchmark" / "tasks"
RESULTS_ROOT = PROJECT_ROOT / "results"


def _git_commit() -> tuple[str, bool]:
    """Returns (commit_hash, is_dirty). A dirty tree means the commit hash
    alone doesn't fully capture what code actually ran."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
            ).stdout.strip()
        )
        return commit, dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", False


def run_one_trial(task: Task, trial: int, model: str, temperature: float, run_dir: Path) -> dict:
    working_dir = Path(tempfile.mkdtemp(prefix=f"{task.id}_trial{trial}_"))
    try:
        shutil.copytree(task.repo_dir, working_dir, dirs_exist_ok=True)
        sandbox = Sandbox(str(working_dir), timeout_seconds=task.budget.timeout_seconds)
        provider = OllamaProvider(model=model, temperature=temperature)

        start = time.monotonic()
        agent_result = run_agent(
            task_description=task.description,
            working_dir=working_dir,
            tests_dir=task.tests_dir,
            provider=provider,
            sandbox=sandbox,
            max_iterations=task.budget.max_iterations,
        )
        wall_clock_seconds = time.monotonic() - start

        # Ground truth is always a fresh hidden-test run here, independent
        # of whatever the agent's own run_tests tool call last reported —
        # it might never have called it, or might be wrong about having
        # succeeded.
        grading = sandbox.run_hidden_tests(str(task.tests_dir))

        trace_path = run_dir / "traces" / f"{task.id}_trial{trial}.jsonl"
        write_trace(agent_result.steps, trace_path)

        tool_steps = [s for s in agent_result.steps if s.tool not in ("finish", "parse_error")]
        parse_errors = [s for s in agent_result.steps if s.tool == "parse_error"]

        return {
            "task_id": task.id,
            "category": task.category.value,
            "trial": trial,
            "passed": grading.passed,
            "finished": agent_result.finished,
            "iterations": agent_result.iterations,
            "tool_calls": len(tool_steps),
            "parse_errors": len(parse_errors),
            "tokens_in": sum(s.tokens_in for s in agent_result.steps),
            "tokens_out": sum(s.tokens_out for s in agent_result.steps),
            "total_latency_ms": sum(s.latency_ms for s in agent_result.steps),
            "wall_clock_seconds": wall_clock_seconds,
        }
    finally:
        shutil.rmtree(working_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="run a single task by id (default: every QA'd task)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument(
        "--resume",
        help="path to an existing run_<timestamp>_<model> dir to continue -- "
        "skips any (task_id, trial) pair already present in its results.json "
        "and appends the rest. Model/temperature/trials/task_ids are read "
        "from that run's own config.json, not from the other CLI flags, so "
        "a resumed run can't silently drift from what it started with.",
    )
    args = parser.parse_args()

    if args.resume:
        run_dir = Path(args.resume)
        config = json.loads((run_dir / "config.json").read_text())
        model, temperature, trial_count = config["model"], config["temperature"], config["trial_count"]
        tasks = [load_task(TASKS_ROOT / tid) for tid in config["task_ids"]]
        results_path = run_dir / "results.json"
        results = json.loads(results_path.read_text()) if results_path.is_file() else []
        done = {(r["task_id"], r["trial"]) for r in results}
        print(f"[runner] resuming {run_dir} -- {len(done)} trial(s) already recorded", flush=True)
    else:
        tasks = [load_task(TASKS_ROOT / args.task)] if args.task else load_tasks(TASKS_ROOT)
        if not tasks:
            raise SystemExit("no QA'd tasks found to run")
        model, temperature, trial_count = args.model, args.temperature, args.trials

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        model_tag = model.replace(":", "-").replace("/", "-")
        run_dir = RESULTS_ROOT / f"run_{timestamp}_{model_tag}"
        run_dir.mkdir(parents=True, exist_ok=True)

        git_commit, git_dirty = _git_commit()
        config = {
            "model": model,
            "temperature": temperature,
            "prompt_version": PROMPT_VERSION,
            "git_commit": git_commit,
            "git_dirty": git_dirty,
            "timestamp": timestamp,
            "trial_count": trial_count,
            "task_ids": [t.id for t in tasks],
        }
        (run_dir / "config.json").write_text(json.dumps(config, indent=2))
        results_path = run_dir / "results.json"
        results = []
        done = set()

    for task in tasks:
        for trial in range(1, trial_count + 1):
            if (task.id, trial) in done:
                continue
            print(f"[runner] {task.id} trial {trial}/{trial_count} ...", flush=True)
            result = run_one_trial(task, trial, model, temperature, run_dir)
            status = "PASS" if result["passed"] else "FAIL"
            print(f"[runner]   -> {status} ({result['iterations']} iterations, "
                  f"{result['tool_calls']} tool calls, {result['wall_clock_seconds']:.1f}s)")
            results.append(result)
            # Rewritten after every trial, not just at the end -- a run that
            # covers many tasks x trials can take hours, and a partial
            # results.json is far more useful than none if the process gets
            # interrupted partway through (the trace files already save
            # incrementally; this closes the gap for the aggregate table).
            results_path.write_text(json.dumps(results, indent=2))

    print(f"\n[runner] wrote {run_dir}/config.json and {results_path}")


if __name__ == "__main__":
    main()
