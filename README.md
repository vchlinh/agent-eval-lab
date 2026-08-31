# Agent Evaluation Lab

A project exploring how to rigorously test AI coding agents — not just whether they "seem to work," but whether they actually work, measured with real statistics.

## The idea

AI agents that write and fix code are everywhere now, but most demos just show a cherry-picked success story. This project builds a small testing harness that runs an AI agent through 20 self-authored coding tasks in a sandboxed environment, checks its work against hidden tests, and reports results with proper confidence intervals and significance tests — the same kind of rigor you'd expect from a real experiment, not a highlight reel.

The AI agent itself is intentionally simple (a ~150-line ReAct loop with five tools: `read_file`, `list_files`, `write_file`, `run_tests`, `finish`). The interesting engineering work is in the *measurement*: how do you fairly and reliably tell if one setup is actually better than another?

## Status

Complete. All three build phases are done — see [`report/REPORT.md`](report/REPORT.md) for the full results.

## What it measures

**The experiment**: does giving the agent the repo tree and full file contents up front (Context B), instead of just the task description (Context A), change how often it succeeds? Same model (`qwen2.5-coder:7b`, local via Ollama), same temperature, tools, sandbox, and iteration budget — context strategy is the only variable that changes.

**Headline result**: Context B raised the per-trial pass rate from 45% to 75%. The real per-task comparison (paired bootstrap over the 20 tasks) puts the effect at +30 percentage points, 95% CI [10%, 50%] — the direction is unlikely to be noise, though McNemar's exact test on the same 20 paired tasks lands at p=0.070, just short of the conventional 0.05 bar. Both numbers are reported together in `report/REPORT.md`, deliberately — a large, CI-backed effect that a small-sample exact test can't fully certify at conventional thresholds is the honest shape of a result at n≈20 tasks, not a contradiction to paper over.

Full breakdown — category-level results, robustness, efficiency, an LLM-as-judge quality assessment (including where the judge itself got things wrong), and a hand-reviewed failure taxonomy — is in [`report/REPORT.md`](report/REPORT.md).

## Methodology

```
benchmark/   20 self-authored tasks (bug fixes, features, edge cases, test-writing,
             refactors, API/docs changes), each with a hidden pytest suite and an
             8-point QA checklist applied before it counts toward the benchmark
agent/       the ReAct agent under test, and the two context strategies (A/B)
harness/     Docker sandbox, the runner that orchestrates task -> agent -> grading,
             and a full JSONL trace of every tool call
evaluation/  correctness / efficiency / robustness metrics, and the LLM-as-judge
             quality scorer (readability, minimality, root-cause-vs-patch)
analysis/    Wilson score CI, paired bootstrap, McNemar's exact test -- implemented
             from closed-form formulas (pure Python, no statsmodels dependency)
report/      generates report/REPORT.md directly from the run/analysis artifacts
```

**Correctness is always decided by the hidden pytest suite, never by the LLM judge.** The judge only scores the quality of already-passing patches (readability, minimality, whether a fix addresses the root cause or papers over it), on a small curated sample — it never decides pass/fail. Two built-in stress cases (a bloated-but-passing patch, a passes-tests-but-papers-over-the-bug patch) are scored first, specifically to check whether the judge itself can be trusted before trusting its verdicts on anything else — it initially failed both.

**Trials are not extra independent tasks.** Each task was run twice per config to measure within-task stochasticity (does the same setup solve the same task reliably?), but the paired statistics (bootstrap, McNemar) compare the two configs over the 20 tasks, not over 40 trials — 20 tasks x 2 trials is 20 experimental units for a cross-config comparison, not 40.

**Every task passed an 8-point QA checklist before counting toward the benchmark**: the starting repo must genuinely fail, the description must be self-sufficient, a reference solution must pass, a structurally different alternative solution must also pass (tests aren't overfit to one implementation), unrelated behavior must stay intact, the hidden tests must not be guessable from the task description or names, and a plausible incomplete solution must actually fail them. This discipline is a small-scale mirror of what OpenAI's July 2026 audit of SWE-Bench Pro found necessary at much larger scale — that audit found roughly 30% of tasks broken in exactly these ways (tests stricter than the stated task, or prompts silently omitting what the tests actually check).

## Reproducing this

```
python -m harness.runner --task task_001              # single task, Context A (default)
python -m harness.runner --context B --trials 2        # full benchmark, Context B, 2 trials/task
python -m evaluation.run_judge_sample                   # curated judge sample
python -m report.build_report                            # regenerate report/REPORT.md
```

Every run writes a self-contained `results/run_<timestamp>_<config>/` folder: `config.json` (model, temperature, prompt version, context mode, git commit hash + dirty flag, trial count), `traces/*.jsonl` (one line per agent loop iteration), and `results.json` (rewritten after every trial, so an interrupted run — this project's own background runs were killed and resumed several times — loses at most the one trial in flight, never the rest).

## Limitations

- **Small n.** 20 tasks means wide confidence intervals on any per-category or significance claim; the report says so explicitly rather than treating a single p-value as the final word.
- **Self-authored benchmark.** Contamination-free (no model has seen these exact tasks), but narrow — 3-4 tiny repos (100-300 lines each), one problem domain style, one difficulty band.
- **One local model, one judge, and the judge shares the model it's judging.** No cross-model generalization claim is made here; `agent/providers.py` is built to make a second provider cheap to add later.
- **Non-determinism.** Temperature 0.2, not 0 — the same task can genuinely pass one trial and fail the next (see the robustness histograms in the report), which is exactly why trials exist as a separate axis from the config comparison.
- **A confound the failure-taxonomy review surfaced, not designed away**: Context B's larger upfront prompt consumes meaningfully more of the local model's fixed context window before a single tool call happens, which can interact with long multi-turn trials (see task_005 in the report) in ways that aren't simply "more information is better." Reported as a limitation, not smoothed over.
- **The judge is not reliably accurate**, even after one round of prompt revision — documented concretely in the report's judge-limitations panel, including a confirmed hallucination on a byte-identical pair of patches.

## Why

This is also a hands-on way to learn core AI/ML evaluation concepts (sandboxing, statistical testing, bias-aware comparisons, LLM-as-judge pitfalls) by building the tooling from scratch rather than just reading about it. `PROGRESS.md` (local, not published) has the full day-by-day build log and every concept covered along the way.
