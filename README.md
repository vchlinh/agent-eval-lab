# Agent Evaluation Lab

A reproducible evaluation framework for measuring the reliability, correctness, and quality of AI coding agents.

## Overview

AI coding agents are increasingly capable of completing software engineering tasks, but demonstrating that an agent _can_ solve a task is different from measuring whether one approach consistently outperforms another.

**Agent Evaluation Lab** explores this problem by building a small-scale experimental framework from scratch. The system evaluates an AI coding agent across **20 self-authored software engineering tasks** in a sandboxed environment, grades solutions using hidden tests, records detailed execution traces, and applies statistical methods to quantify uncertainty and compare experimental conditions.

The project focuses on the **measurement layer** rather than building a sophisticated agent. The agent itself is intentionally lightweight: a ~150-line ReAct loop with five tools:

- `list_files`
- `read_file`
- `write_file`
- `run_tests`
- `finish`

The primary engineering challenge is therefore evaluation: **how can we determine whether an observed improvement is real, reproducible, and meaningful rather than an artifact of task selection, randomness, or flawed evaluation?**

## Results

The experiment compares two context strategies:

- **Context A:** The agent receives only the task description.
- **Context B:** The agent receives the task description plus the repository tree and full file contents.

All other experimental conditions remain fixed: model, temperature, tools, sandbox, and iteration budget.

Using the local `qwen2.5-coder:7b` model through Ollama:

| Metric                  | Context A |            Context B |
| ----------------------- | --------: | -------------------: |
| Per-trial pass rate     |       45% |                  75% |
| Difference              |         — |           **+30 pp** |
| 95% paired bootstrap CI |         — | **[+10 pp, +50 pp]** |
| McNemar's exact test    |         — |        **p = 0.070** |

The results suggest a substantial improvement under Context B, while the exact paired significance test does not cross the conventional 0.05 threshold. These findings are reported together rather than reduced to a single statistical conclusion: with only **20 experimental units**, the confidence interval and hypothesis test provide complementary information about the uncertainty of the observed effect.

The complete analysis includes:

- Overall correctness
- Per-category performance
- Within-task robustness
- Efficiency
- LLM-as-judge quality assessment
- Hand-reviewed failure taxonomy
- Statistical uncertainty and significance testing

See [`report/REPORT.md`](report/REPORT.md) for the complete results and analysis.

## Methodology

```text
benchmark/
  20 self-authored coding tasks covering bug fixes, features, edge cases,
  test-writing, refactoring, and API/documentation changes. Each task
  includes hidden pytest tests and passes an 8-point QA checklist.

agent/
  The ReAct coding agent and the two experimental context strategies.

harness/
  Docker sandbox, experiment runner, task orchestration, grading, and
  JSONL execution tracing.

evaluation/
  Correctness, efficiency, robustness, and LLM-as-judge quality metrics.

analysis/
  Wilson score confidence intervals, paired bootstrap confidence intervals,
  and McNemar's exact test implemented in pure Python.

report/
  Report-generation pipeline that produces report/REPORT.md from experiment
  and analysis artifacts.
```
