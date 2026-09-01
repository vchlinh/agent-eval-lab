# Agent Evaluation Lab

A reproducible evaluation framework for measuring the reliability, correctness, and quality of AI coding agents.

## Overview

AI coding agents are increasingly capable of completing software engineering tasks, but demonstrating that an agent can solve a task is different from measuring whether one approach consistently outperforms another.

Agent Evaluation Lab explores this problem by building a small-scale experimental framework from scratch. The system evaluates an AI coding agent across 20 self-authored software engineering tasks in a sandboxed environment, grades solutions using hidden tests, records detailed execution traces, and applies statistical methods to quantify uncertainty and compare experimental conditions.

The project focuses on the measurement layer rather than building a sophisticated agent. The agent itself is intentionally lightweight: a ~150-line ReAct loop with five tools:

- `list_files`
- `read_file`
- `write_file`
- `run_tests`
- `finish`

## Results

The experiment compares two context strategies:

- **Context A:** The agent receives only the task description.
- **Context B:** The agent receives the task description plus the repository tree and full file contents.

All other experimental conditions remain fixed: model, temperature, tools, sandbox, and iteration budget.

Using the local `qwen2.5-coder:7b` model through Ollama:

| Metric | Context A | Context B |
|---|---|---|
| Per-trial pass rate | 45% | 75% |
| Difference | — | **+30 pp** |
| 95% paired bootstrap CI | — | **[+10 pp, +50 pp]** |
| McNemar's exact test | — | **p = 0.070** |

The results suggest a substantial improvement under Context B, while the exact paired significance test does not cross the conventional 0.05 threshold. With only 20 experimental units, the confidence interval and hypothesis test provide complementary information about that uncertainty, so both are reported rather than collapsed into one conclusion.

The complete analysis includes:

- Overall correctness
- Per-category performance
- Within-task robustness
- Efficiency
- LLM-as-judge quality assessment
- Hand-reviewed failure taxonomy
- Statistical uncertainty and significance testing

See [`report/REPORT.md`](report/REPORT.md) for the full results.

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

## Evaluation design

Correctness is determined exclusively by hidden tests; the LLM judge never decides whether a task passes. It is used only to evaluate the quality of patches that have already passed, including:

- Readability
- Minimality
- Root-cause resolution vs. superficial patching

The judge is evaluated separately using two deliberately constructed stress cases:

1. A bloated but passing patch
2. A patch that passes the tests while papering over the underlying bug

The initial judge configuration failed both stress cases, and that failure is documented as part of the evaluation rather than hidden.

## Experimental units

Each task is run twice per configuration.

These repeated trials measure within-task stochasticity: whether the same configuration reliably solves the same task across runs.

However, the cross-configuration statistical comparison uses 20 tasks as the experimental units, not 40 trials.

## Benchmark quality control

Before entering the benchmark, every task passes an 8-point QA checklist covering:

1. The starting repository genuinely fails the intended behavior.
2. The task description is self-contained.
3. A reference solution passes the hidden tests.
4. A structurally different valid solution also passes.
5. Unrelated behavior remains intact.
6. Hidden tests cannot be trivially inferred from task names or descriptions.
7. A plausible incomplete solution fails the hidden tests.
8. The task's tests evaluate the intended behavior rather than implementation-specific details.

This validation step is intended to reduce common benchmark-quality problems such as ambiguous specifications, overfitted tests, and tests that check behavior not described in the task.

## Reproducing the experiment

Run a single task using Context A:

```
python -m harness.runner --task task_001
```

Run the full benchmark using Context B with two trials per task:

```
python -m harness.runner --context B --trials 2
```

Run the curated LLM-as-judge validation sample:

```
python -m evaluation.run_judge_sample
```

Regenerate the report:

```
python -m report.build_report
```

## Experiment artifacts

Each run produces a self-contained directory:

```
results/run_<timestamp>_<config>/
├── config.json
├── traces/
│   └── *.jsonl
└── results.json
```

`config.json` records the experimental configuration, including:

- Model
- Temperature
- Prompt version
- Context mode
- Git commit hash
- Repository dirty state
- Trial count

`traces/*.jsonl` contains the agent's execution trace, with one JSON record per agent loop iteration.

`results.json` is updated after each completed trial, allowing interrupted experiments to resume without losing previously completed results.

## Statistical Analysis

The project implements its statistical analysis directly in Python without relying on statsmodels.

### Confidence intervals

Wilson score intervals are used for binomial pass-rate estimates.

Paired bootstrap confidence intervals are used to estimate uncertainty around the difference between Context A and Context B across the 20 tasks.

### Significance testing

McNemar's exact test is used for the paired comparison because each task is evaluated under both experimental conditions.

This pairing controls for differences in task difficulty: instead of asking whether two groups of different tasks perform differently, the analysis asks whether the same tasks are more likely to pass under one configuration than the other.

## Limitations

This experiment is intentionally small and should not be interpreted as a general benchmark of AI coding agents.

- **Small sample size.** The benchmark contains only 20 tasks, producing substantial uncertainty, particularly for category-level and significance estimates.
- **Self-authored benchmark.** The tasks are designed to avoid contamination from existing benchmarks, but they cover only a narrow range of repositories, problem styles, and difficulty levels.
- **Limited model coverage.** The experiment uses one local model (qwen2.5-coder:7b) and one LLM judge. No cross-model generalization claim is made.
- **Stochastic execution.** The agent runs at temperature 0.2, so identical configurations can produce different outcomes. Repeated trials are therefore treated as an explicit dimension of the experiment.
- **Context-window effects.** Context B provides substantially more information to the model upfront, which also consumes more of the model's available context window. This can interact with long multi-turn tasks and complicate the interpretation of the context manipulation.
- **LLM-as-judge reliability.** The judge is not perfectly reliable. The evaluation includes documented cases where it produced incorrect assessments, including a confirmed hallucination when evaluating byte-identical patches.

## Why This Project?

Agent Evaluation Lab is both an evaluation study and a hands-on exploration of modern AI engineering, building measurement infrastructure alongside the agent rather than treating evaluation as an afterthought:

- Sandboxed agent execution
- Reproducible experiment configuration
- Execution tracing
- Benchmark QA
- Correctness and efficiency metrics
- Statistical inference
- Paired experimental design
- LLM-as-judge validation
- Failure analysis

The goal is to develop practical intuition for a central problem in AI engineering:

Building an agent is only half the problem. The other half is knowing whether it actually works.

For development notes and the complete day-by-day build process, see PROGRESS.md.
