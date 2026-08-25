"""
Tracer: serializes an agent run's steps to JSONL — one line per loop
iteration, exactly the {timestamp, iteration, tool, args, result,
tokens_in, tokens_out, latency_ms} shape specified in the plan. This is
the file evaluation/efficiency.py and later analysis code read back to
compute iteration counts, tool-call patterns, latency, and cost.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from agent.react_agent import AgentStep


def write_trace(steps: list[AgentStep], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for step in steps:
            f.write(json.dumps(dataclasses.asdict(step)) + "\n")


def read_trace(path: Path) -> list[dict]:
    path = Path(path)
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
