"""
LLM-as-judge: scores the QUALITY of a finished, already-passing patch --
readability, minimality, and whether it fixes the root cause rather than
papering over a symptom. Ground rule: the judge NEVER decides pass/fail
(that's always the hidden pytest result computed by harness/runner.py) and
only ever runs on a small curated sample, never every trial -- see the
project's ground rules and plan.md.

Includes two built-in stress cases (a bloated-but-passing solution and a
passes-tests-but-papers-over-the-bug solution, both hand-verified to
actually pass task_001's real hidden tests) so the judge's own behavior
gets sanity-checked against patches with a known "should score badly on
X" answer before it's trusted on real agent patches.
"""

from __future__ import annotations

import difflib
import json
import random
import statistics
from pathlib import Path

from agent.providers import Provider
from benchmark.schema import Task, load_task
from harness.tracer import read_trace

RUBRIC_DIMENSIONS = ("readability", "minimality", "root_cause_vs_patch")

JUDGE_SYSTEM_PROMPT = """You are a senior software engineer reviewing a code \
patch written by another engineer (or an AI coding agent) to fix or extend a \
small Python repository. The patch is already known to pass the test suite \
-- do not re-judge correctness. A patch passing tests is NOT by itself \
evidence that it fixed the root cause -- a patch can pass every test while \
leaving the actual bug in place, by detecting the bad outcome after the \
fact and patching it up, or by handling only the specific inputs the tests \
happen to check. Before scoring, identify in your own reasoning exactly \
which lines the patch changed, and whether the task description's stated \
bug or cause is DIRECTLY addressed by those specific lines, or whether the \
original buggy code/logic is still present with something bolted on \
afterward to compensate for it.

Score the QUALITY of the patch on three dimensions, each from 1 (poor) to \
5 (excellent):

- readability: is the change clear, idiomatic, and easy for another \
engineer to follow?
- minimality: does the patch make the smallest reasonable change to \
accomplish the task? Penalize unrelated edits, dead code, unused \
parameters/config, or introducing new classes/abstractions a one- or \
few-line fix didn't need.
- root_cause_vs_patch: does the change directly fix the specific \
mechanism described as buggy, or does it leave that mechanism unchanged \
and compensate for its output elsewhere? A patch that never touches the \
described buggy logic should score LOW here even if it passes every test.

Respond with EXACTLY one JSON object and nothing else:
{"readability": <1-5>, "minimality": <1-5>, "root_cause_vs_patch": <1-5>, "rationale": "<2-3 sentences, including which lines you identified as the fix>"}
"""

JUDGE_COMPARISON_PROMPT = """You are a senior software engineer comparing two \
independent patches written to solve the SAME task in the SAME small Python \
repository. Both patches are already known to pass the test suite -- do not \
re-judge correctness. Decide which patch is the higher-quality solution, \
based on readability, minimality, and whether it fixes the root cause \
rather than the symptom.

Respond with EXACTLY one JSON object and nothing else:
{"preferred": "Patch 1" or "Patch 2", "rationale": "<2-3 sentences>"}
"""


def unified_diff_for_file(original_content: str, new_content: str, rel_path: str) -> str:
    diff = difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    )
    return "".join(diff)


def extract_final_diff(task: Task, trace_path: Path) -> str:
    """
    Reconstructs the net effect of one agent run as a unified diff against
    the task's starting repo/ files: replays every write_file step in
    trace order and keeps only each path's LAST write (an agent may
    overwrite the same file several times before finishing), then diffs
    that final content against the file's original content. This judges
    what the agent actually shipped, not the raw trace, which mixes in
    dead-end intermediate edits the agent itself abandoned.
    """
    final_content: dict[str, str] = {}
    for step in read_trace(trace_path):
        if step["tool"] == "write_file":
            final_content[step["args"]["path"]] = step["args"].get("content", "")

    if not final_content:
        return ""  # agent never wrote anything

    parts = []
    for rel_path, new_content in final_content.items():
        original_path = task.repo_dir / rel_path
        original_content = original_path.read_text() if original_path.is_file() else ""
        parts.append(unified_diff_for_file(original_content, new_content, rel_path))
    return "\n".join(p for p in parts if p)


def _parse_judgment(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError("judge response contained no JSON object")
    obj, _ = json.JSONDecoder().raw_decode(text, start)
    for dim in RUBRIC_DIMENSIONS:
        if dim not in obj:
            raise ValueError(f"judge response missing '{dim}'")
        if not isinstance(obj[dim], (int, float)) or not (1 <= obj[dim] <= 5):
            raise ValueError(f"judge response '{dim}' must be 1-5, got {obj[dim]!r}")
    return obj


def judge_patch(task_description: str, diff_text: str, provider: Provider) -> dict:
    """One judgment call, scored on RUBRIC_DIMENSIONS. Raises ValueError on
    a malformed judge response rather than silently guessing -- a judge
    score is only useful if it's actually the rubric being scored, not a
    parsing artifact papered over."""
    if not diff_text.strip():
        return {dim: 1 for dim in RUBRIC_DIMENSIONS} | {"rationale": "agent made no changes"}

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Task:\n{task_description}\n\nPatch (unified diff):\n{diff_text}"},
    ]
    result = provider.complete(messages)
    return _parse_judgment(result.text)


def judge_patch_repeated(task_description: str, diff_text: str, provider: Provider, n: int = 3) -> dict:
    """
    Runs judge_patch n times (self-consistency check) and reports each
    dimension's individual scores plus mean and spread (max - min) -- a
    judge whose scores swing wildly run-to-run on the SAME unchanged patch
    is not trustworthy yet, and that has to stay visible rather than get
    averaged away.
    """
    judgments = []
    for _ in range(n):
        try:
            judgments.append(judge_patch(task_description, diff_text, provider))
        except ValueError as e:
            judgments.append({"error": str(e)})

    summary: dict = {"n": n, "judgments": judgments}
    for dim in RUBRIC_DIMENSIONS:
        scores = [j[dim] for j in judgments if dim in j]
        if scores:
            summary[dim] = {"scores": scores, "mean": statistics.mean(scores), "spread": max(scores) - min(scores)}
    return summary


def _parse_comparison(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError("judge comparison response contained no JSON object")
    obj, _ = json.JSONDecoder().raw_decode(text, start)
    if obj.get("preferred") not in ("Patch 1", "Patch 2"):
        raise ValueError(f"judge comparison 'preferred' must be 'Patch 1' or 'Patch 2', got {obj.get('preferred')!r}")
    return obj


def compare_patches_blind(
    task_description: str,
    diff_a: str,
    diff_b: str,
    provider: Provider,
    seed: int | None = None,
) -> dict:
    """
    Blind, order-randomized head-to-head preference between two patches
    for the SAME task: the judge only ever sees "Patch 1"/"Patch 2", never
    which config produced which, and which one is labeled "1" is
    randomized per call so a position bias in the model can't
    systematically favor one config over the other. The label mapping is
    un-shuffled afterward so the CALLER can compare against the real "a"
    (Config A) / "b" (Config B) identity -- the blinding only applies to
    what the model itself is shown.
    """
    rng = random.Random(seed)
    a_shown_first = rng.random() < 0.5
    patch1_label, patch1_diff = ("a", diff_a) if a_shown_first else ("b", diff_b)
    patch2_label, patch2_diff = ("b", diff_b) if a_shown_first else ("a", diff_a)

    user_prompt = (
        f"Task:\n{task_description}\n\n"
        f"Patch 1 (unified diff):\n{patch1_diff}\n\n"
        f"Patch 2 (unified diff):\n{patch2_diff}"
    )
    messages = [
        {"role": "system", "content": JUDGE_COMPARISON_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    result = provider.complete(messages)
    parsed = _parse_comparison(result.text)
    preferred_config = patch1_label if parsed["preferred"] == "Patch 1" else patch2_label

    return {
        "preferred_config": preferred_config,
        "rationale": parsed["rationale"],
        "a_shown_first": a_shown_first,
    }


# --- Built-in judge stress cases -------------------------------------------
#
# Two patches, both hand-verified (2026-08-31, `python3 -m pytest` against a
# real copy of task_001's repo + hidden tests: 37/37 passed for each) to
# actually pass task_001's hidden tests, so both are legitimate "already
# passing" inputs to the judge -- exactly the kind the judge will see for
# real. Each has a known-bad answer on ONE rubric dimension by construction:
#
# - bloated-but-passing: correct, but wraps a one-line off-by-one fix in an
#   unused PaginationConfig dataclass, an unused "strict" flag, and a
#   Paginator class -- should score LOW on minimality despite being fully
#   correct and reasonably readable.
# - papers-over-the-bug: correct on every hidden-test case, but leaves the
#   actual off-by-one bug (`len(items) - 1`) untouched and bolts on a
#   leftover-items patch afterward instead of fixing the loop bound --
#   should score LOW on root_cause_vs_patch despite passing every test.

_BLOATED_BUT_PASSING = '''"""Pagination utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence


@dataclass
class PaginationConfig:
    """Configuration object controlling how pagination behaves."""

    page_size: int
    strict: bool = True


class Paginator:
    """A general-purpose paginator supporting arbitrary sequences."""

    def __init__(self, config: PaginationConfig):
        self.config = config

    def _validate(self, items: Sequence[Any]) -> None:
        if self.config.page_size <= 0:
            raise ValueError("page_size must be positive")  # defensive, never exercised

    def paginate(self, items: Sequence[Any]) -> List[List[Any]]:
        self._validate(items)
        pages: List[List[Any]] = []
        buffer: List[Any] = []
        for index, item in enumerate(items):
            buffer.append(item)
            is_last_item = index == len(items) - 1
            if len(buffer) == self.config.page_size or is_last_item:
                pages.append(buffer)
                buffer = []
        return pages


def paginate(items, page_size):
    """Split items into pages of at most page_size items each.

    Thin wrapper around the Paginator class, provided for backwards
    compatibility with callers expecting a plain function interface.
    """
    paginator = Paginator(PaginationConfig(page_size=page_size))
    return paginator.paginate(items)
'''

_PAPERS_OVER_BUG = '''def paginate(items, page_size):
    """Split items into pages of at most page_size items each."""
    pages = []
    for i in range(0, len(items) - 1, page_size):
        pages.append(items[i:i + page_size])
    covered = sum(len(p) for p in pages)
    if covered < len(items):
        pages.append(items[covered:])
    return pages
'''


def built_in_stress_cases(tasks_root: Path) -> list[dict]:
    """
    Returns the two stress cases as curated-sample entries, in the same
    shape a real trace-derived sample entry would use: {task_id,
    task_description, diff_text, label}. `label` documents which
    dimension the case is designed to catch, purely for the human
    reviewing judge output -- never shown to the judge itself.
    """
    task = load_task(Path(tasks_root) / "task_001")
    original = task.repo_dir.joinpath("paginate.py").read_text()

    return [
        {
            "task_id": task.id,
            "task_description": task.description,
            "diff_text": unified_diff_for_file(original, _BLOATED_BUT_PASSING, "paginate.py"),
            "label": "stress:bloated_but_passing (expect low minimality)",
        },
        {
            "task_id": task.id,
            "task_description": task.description,
            "diff_text": unified_diff_for_file(original, _PAPERS_OVER_BUG, "paginate.py"),
            "label": "stress:papers_over_bug (expect low root_cause_vs_patch)",
        },
    ]
