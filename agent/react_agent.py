"""
Minimal ReAct agent: alternates Reason (ask the model what to do) and Act
(run one of five tools), feeding each tool's result back as the next
observation, until the model calls finish() or the iteration budget runs
out. Deliberately small — no planner, no memory beyond the transcript, no
subagents. See PROMPT_VERSION below for the exact instructions it's given.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.providers import Provider
from harness.sandbox import Sandbox

PROMPT_VERSION = "react_v2"
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.md").read_text()


@dataclasses.dataclass
class AgentStep:
    timestamp: str
    iteration: int
    tool: str
    args: dict
    result: str
    tokens_in: int
    tokens_out: int
    latency_ms: float


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclasses.dataclass
class AgentRunResult:
    finished: bool
    iterations: int
    steps: list[AgentStep]
    summary: str


def _safe_path(working_dir: Path, rel_path: str) -> Path | None:
    """Resolve rel_path against working_dir, refusing anything that would
    escape it (e.g. an absolute path or a `../../` traversal). File tools
    run directly on the host, unlike run_tests, so this containment check
    is the only thing stopping the agent from touching files outside the
    task's working copy."""
    candidate = (working_dir / rel_path).resolve()
    try:
        candidate.relative_to(working_dir.resolve())
    except ValueError:
        return None
    return candidate


def execute_tool(working_dir: Path, sandbox: Sandbox, tests_dir: Path, tool: str, args: dict) -> str:
    if tool == "list_files":
        base = _safe_path(working_dir, args.get("path", "."))
        if base is None:
            return "ERROR: path escapes the task's working directory"
        if not base.exists():
            return f"ERROR: path not found: {args.get('path', '.')}"
        paths = sorted(str(p.relative_to(working_dir)) for p in base.rglob("*") if p.is_file())
        return "\n".join(paths) if paths else "(no files)"

    if tool == "read_file":
        path = _safe_path(working_dir, args.get("path", ""))
        if path is None:
            return "ERROR: path escapes the task's working directory"
        if not path.is_file():
            return f"ERROR: file not found: {args.get('path')}"
        return path.read_text()

    if tool == "write_file":
        path = _safe_path(working_dir, args.get("path", ""))
        if path is None:
            return "ERROR: path escapes the task's working directory"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.get("content", ""))
        return f"wrote {args.get('path')}"

    if tool == "run_tests":
        result = sandbox.run_hidden_tests(str(tests_dir))
        status = "PASSED" if result.passed else "FAILED"
        return f"{status} (exit_code={result.exit_code})\n{result.stdout}\n{result.stderr}".strip()

    return f"ERROR: unknown tool '{tool}' — valid tools: list_files, read_file, write_file, run_tests, finish"


def _extract_fenced_content(remainder: str) -> str:
    """Pull the raw text out of the first ```-fenced block in `remainder`,
    dropping an optional language tag on the opening fence line."""
    fence_start = remainder.find("```")
    if fence_start == -1:
        raise ValueError("write_file response is missing its fenced content block")
    after_open = remainder[fence_start + 3 :]
    if "\n" in after_open:
        after_open = after_open.split("\n", 1)[1]
    fence_end = after_open.find("```")
    if fence_end == -1:
        raise ValueError("write_file response's fenced content block is not closed")
    return after_open[:fence_end]


def parse_step(text: str) -> dict:
    """Extract the JSON header the model was told to respond with. Finds
    the first '{' anywhere in the text (so a leading markdown fence around
    just the header doesn't matter) and parses one JSON value from there
    with json.JSONDecoder.raw_decode, ignoring anything after it — this is
    what makes it safe to follow the header with a separate fenced code
    block for write_file, instead of naively searching for the *last*
    '}' in the whole response, which a trailing fence could contain."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found in model response")
    try:
        step, end = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON header: {e}") from e
    if "tool" not in step:
        raise ValueError("response JSON is missing the 'tool' field")
    if step["tool"] == "write_file":
        step.setdefault("args", {})["content"] = _extract_fenced_content(text[end:])
    return step


def run_agent(
    task_description: str,
    working_dir: Path,
    tests_dir: Path,
    provider: Provider,
    sandbox: Sandbox,
    max_iterations: int,
) -> AgentRunResult:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task:\n{task_description}"},
    ]
    steps: list[AgentStep] = []

    for iteration in range(1, max_iterations + 1):
        result = provider.complete(messages)
        messages.append({"role": "assistant", "content": result.text})

        try:
            step = parse_step(result.text)
        except ValueError as e:
            observation = f"ERROR: {e}. Respond with exactly one JSON object as instructed."
            messages.append({"role": "user", "content": observation})
            steps.append(AgentStep(_now(), iteration, "parse_error", {}, observation,
                                    result.tokens_in, result.tokens_out, result.latency_ms))
            continue

        tool, args = step["tool"], step.get("args", {})

        if tool == "finish":
            summary = args.get("summary", "")
            steps.append(AgentStep(_now(), iteration, "finish", args, summary,
                                    result.tokens_in, result.tokens_out, result.latency_ms))
            return AgentRunResult(finished=True, iterations=iteration, steps=steps, summary=summary)

        observation = execute_tool(working_dir, sandbox, tests_dir, tool, args)
        messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        steps.append(AgentStep(_now(), iteration, tool, args, observation,
                                result.tokens_in, result.tokens_out, result.latency_ms))

    return AgentRunResult(finished=False, iterations=max_iterations, steps=steps,
                           summary="max iterations reached without calling finish")
