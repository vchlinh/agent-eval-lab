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
    raw_response: str = ""


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
    """Pull the real file content out of `remainder`, which may contain
    more than one ```-fenced block. Some models wrap the JSON header
    itself in its own fence despite being told not to, sometimes with a
    stray caption line before the real content's fence — so the *first*
    fence pair isn't reliably the right one. Instead, pair up every fence
    found and take the longest resulting block: real file content is
    reliably much longer than a stray fence-closer or a one-line caption."""
    positions = []
    idx = 0
    while True:
        idx = remainder.find("```", idx)
        if idx == -1:
            break
        positions.append(idx)
        idx += 3

    if len(positions) < 2:
        raise ValueError("write_file response is missing its fenced content block")

    # An odd count means one fence has no partner within `remainder` —
    # this happens when the model wraps the JSON header in its own fence
    # (against instructions): that wrapper's *opening* fence appears
    # before the header, outside `remainder` entirely, so only its
    # *closing* fence shows up here, unmatched, first. Drop it before
    # pairing, or every pair after it is misaligned by one.
    if len(positions) % 2 == 1:
        positions = positions[1:]

    candidates = []
    for start, end in zip(positions[0::2], positions[1::2]):
        block = remainder[start + 3 : end]
        if "\n" in block:
            block = block.split("\n", 1)[1]  # drop an optional language tag
        candidates.append(block)

    return max(candidates, key=len)


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
    # On macOS, tempfile.mkdtemp() returns a path through a symlink (e.g. /var/...,
    # which is really /private/var/...) — without this, _safe_path's own
    # .resolve() call would follow that symlink while working_dir stayed
    # unresolved, making every relative_to() check fail even for files
    # genuinely inside the working directory.
    working_dir = Path(working_dir).resolve()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task:\n{task_description}"},
    ]
    steps: list[AgentStep] = []

    for iteration in range(1, max_iterations + 1):
        try:
            result = provider.complete(messages)
        except OSError as e:
            # A slow generation exceeding the provider's timeout shouldn't 
            # destroy every step already recorded — end the run here, with 
            # whatever trace data exists so far, instead of letting the 
            # exception propagate and losing it all.
            summary = f"provider error: {e}"
            steps.append(AgentStep(_now(), iteration, "provider_error", {}, summary, 0, 0, 0.0))
            return AgentRunResult(finished=False, iterations=iteration, steps=steps, summary=summary)

        messages.append({"role": "assistant", "content": result.text})

        try:
            step = parse_step(result.text)
        except ValueError as e:
            observation = f"ERROR: {e}. Respond with exactly one JSON object as instructed."
            messages.append({"role": "user", "content": observation})
            steps.append(AgentStep(_now(), iteration, "parse_error", {}, observation,
                                    result.tokens_in, result.tokens_out, result.latency_ms,
                                    raw_response=result.text))
            continue

        tool, args = step["tool"], step.get("args", {})

        if tool == "finish":
            summary = args.get("summary", "")
            steps.append(AgentStep(_now(), iteration, "finish", args, summary,
                                    result.tokens_in, result.tokens_out, result.latency_ms,
                                    raw_response=result.text))
            return AgentRunResult(finished=True, iterations=iteration, steps=steps, summary=summary)

        observation = execute_tool(working_dir, sandbox, tests_dir, tool, args)
        messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        steps.append(AgentStep(_now(), iteration, tool, args, observation,
                                result.tokens_in, result.tokens_out, result.latency_ms,
                                raw_response=result.text))

    return AgentRunResult(finished=False, iterations=max_iterations, steps=steps,
                           summary="max iterations reached without calling finish")
