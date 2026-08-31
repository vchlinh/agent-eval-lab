"""
Builds the agent's initial user message under one of two context strategies
— this is the Day 3 experiment's single independent variable. Everything
else (model, tools, sandbox, temperature, iteration budget, prompt version)
stays identical between the two; only how much of the repo the agent sees
*before* its first action changes.

Context A: task description only. The agent must call list_files/read_file
itself to discover the repo before it can act — this is what Day 1/2 already
ran.

Context B: task description + repo tree + full contents of every file in
the repo. These task repos are deliberately tiny (6-135 lines total per
plan.md's own tally), so "relevant file excerpts" from the plan honestly
means "the whole repo" here — there's no cherry-picking of which files
count as relevant, which would risk quietly leaking a hint about where the
bug lives.
"""

from __future__ import annotations

from pathlib import Path

CONTEXT_MODES = ("A", "B")


def build_initial_message(task_description: str, working_dir: Path, context_mode: str) -> str:
    if context_mode not in CONTEXT_MODES:
        raise ValueError(f"unknown context_mode {context_mode!r}, expected one of {CONTEXT_MODES}")

    if context_mode == "A":
        return f"Task:\n{task_description}"

    working_dir = Path(working_dir)
    paths = sorted(p for p in working_dir.rglob("*") if p.is_file())
    tree = "\n".join(str(p.relative_to(working_dir)) for p in paths)

    sections = [f"Task:\n{task_description}", f"Repository structure:\n{tree}"]
    for path in paths:
        rel = path.relative_to(working_dir)
        sections.append(f"### {rel}\n```\n{path.read_text()}\n```")

    return "\n\n".join(sections)
