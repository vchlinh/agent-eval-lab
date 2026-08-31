# Agent Evaluation Lab -- Day 3 Report

Context A (task description only) vs. Context B (task description + repo tree + full file contents), same model (qwen2.5-coder:7b, local via Ollama), temperature 0.2, same tools/sandbox/iteration budget, 20 tasks x 2 trials per config.

## Leaderboard

Same model, temperature, tool set, sandbox, and iteration budget for both configs -- context strategy is the only variable that differs.

| Config | Trials | Pass rate | Wilson 95% CI |
|---|---|---|---|
| A (task description only) | 40 | 45% (18/40) | [31%, 60%] |
| B (+ repo tree + files) | 40 | 75% (30/40) | [60%, 86%] |

## Category breakdown

Per-trial pass rate (not Wilson-CI'd individually -- each category is only 2-4 tasks x 2 trials, too few for a meaningful per-category interval; use the overall CIs above for the headline claim).

| Category | Config A | Config B | Delta |
|---|---|---|---|
| bug_fix | 60% | 70% | +10pp |
| feature | 50% | 62% | +12pp |
| edge_case | 83% | 83% | +0pp |
| test_writing | 0% | 83% | +83pp |
| refactor | 17% | 67% | +50pp |
| api_change_docs | 50% | 100% | +50pp |

## Statistics (the actual per-task comparison)

**This is the real Day-3 result, not the leaderboard above.** The leaderboard's 40 trials per config are not 40 independent experimental units -- the 20 tasks are, since each task was run twice under the same config. Every test below operates over those 20 tasks, paired by task id.

- **Paired bootstrap** on task-level success-rate difference (B − A), 10,000 resamples of 20 tasks: observed diff **+30 percentage points**, 95% CI **[10%, 50%]**.
- **McNemar's exact test** on the paired pass/fail table (a task counts as "pass" if at least 1 of its 2 trials passed): both_pass=12, both_fail=0, A-only=1, B-only=7, **p = 0.070**.

The bootstrap CI excludes zero -- the direction of the effect is unlikely to be noise. The exact McNemar test, on only 20 paired tasks, does not clear the conventional p<0.05 bar. Both statements are true simultaneously and both belong in this report: a large, bootstrap-CI-backed effect that a small-sample exact test can't fully certify at conventional thresholds is the honest shape of a result at n≈20 tasks, not a contradiction to resolve by picking whichever number looks better.

## Robustness and efficiency

Robustness: how many of the 20 tasks land in each per-task pass fraction (2/2 = reliably solvable, 1/2 = solvable but inconsistent, 0/2 = never solved in either trial).

| Config | 2/2 | 1/2 | 0/2 |
|---|---|---|---|
| A | 5 | 8 | 7 |
| B | 11 | 8 | 1 |

Efficiency (median per trial -- median, not mean, since several trials hit the full iteration budget and would skew a mean-based view):

| Config | Iterations | Tool calls | Wall-clock | Est. cost |
|---|---|---|---|---|
| A | 9 | 8 | 421s | $0.032 |
| B | 3 | 2 | 151s | $0.010 |

## LLM-judge quality assessment, and where the judge itself broke

The judge (same local model as the agent-under-test, qwen2.5-coder:7b) scores readability, minimality, and root-cause-vs-patch on a curated sample of already-passing patches -- it never decides pass/fail. Full methodology and every raw score: `evaluation/judge.py`, `evaluation/run_judge_sample.py`, and `results/judge_sample_20260831T220733Z/report.json`.

### Judge-limitations panel (what it got wrong, not just its scores)

Two built-in stress cases (a bloated-but-passing patch, a passes-tests-but-papers-over-the-bug patch, both hand-verified to actually pass task_001's real hidden tests) were scored first, before trusting the judge on real patches:

- **First prompt: the judge failed both stress tests.** It rated the papers-over-the-bug patch's root_cause_vs_patch at 4-5/5 ("correctly addresses the root cause" -- false, the buggy line was never touched), and the bloated patch's minimality at 3-4/5 despite unmistakable unused classes and config objects.
- **After one prompt revision** (require identifying the changed lines before scoring): root_cause_vs_patch on the papers-over-bug case correctly dropped to 1.67/5 -- but the same stricter prompt then *also* dropped root_cause_vs_patch to 2/5 on the bloated patch, which genuinely does fix the root cause, just verbosely. One fix in one direction introduced a new false negative in the other. Documented as a real limitation of a 7B local judge rather than tuned further against these two known fixtures.

Hand-verifying every head-to-head rationale against the real diffs (not just reading the scores) surfaced further, concrete failures on real patches:

- **task_001 -- a clear hallucination.** Config A's and B's patches were byte-identical. The judge's blind comparison still invented a difference, claiming "Patch 2 ... does not fix the bug" -- false; both patches passed.
- **task_002 -- inconsistency without hallucination.** Same byte-identical patches, correctly called identical in the head-to-head call -- but two independent rubric calls on that exact same diff still returned 5/5/5 vs. 4/4/4.5. The absolute 1-5 scores carry meaningfully more noise than the blind pairwise preference does.
- **task_008 -- misattributed reasoning.** The two patches differed only by a stray comment line; the judge preferred one "because it defines the helper function at the top of the file" -- true of both patches equally, not the actual difference between them.
- **task_009 -- checked and correct**, included deliberately alongside the failures above: the judge's stated reasoning (preferring the patch that avoided an unnecessary `__repr__` change) matched the real diff. The judge is not reliably wrong, just not reliably right -- both need reporting together.

## Failure taxonomy (8 hand-read traces)

**Destructive whole-file overwrite -- `write_file` always replaces a file's entire content, so whenever the model doesn't faithfully reproduce every part of a file it's rewriting, whatever it omits is silently deleted -- is the single most common root cause in this hand-reviewed sample, appearing in 5 of 8 traces, under BOTH configs. It is a tool/agent-design property, not a context-availability one, and it means a real share of both configs' raw pass/fail numbers reflects 'did this trial happen to delete something it shouldn't have' rather than context strategy.**

| Trace | Outcome | Tags | Note |
|---|---|---|---|
| task_005 / Config A / trial 1 | PASS | implementation (destructive overwrite), recovery (successful) | First edit dropped an existing `Note` class and a module-level constant. The resulting NameError was caught and fixed on the very next attempt. |
| task_005 / Config B / trial 1 | FAIL | implementation (destructive overwrite), loop | Identical destructive-overwrite mistake as the Config A trial above, despite Context B having handed it the complete original file verbatim. Recovered from that, but then repeated an identical (correct) diagnosis of a second bug for 7+ iterations without ever fixing it. tokens_in climbed from 1,233 to 4,034-4,082 by the final iterations -- at the local model's actual 4096-token context window. |
| task_016 / Config A / trial 1 | FAIL | understanding, test-interpretation, loop | Wrote a test asserting a hallucinated API (`add_expense(...)`) before reading the real file; corrected the API call after reading it, but the test still asserted custom-object equality the class doesn't support, then rewrote byte-identical content for the remaining iterations. |
| task_014 / Config A / trial 2 | FAIL | loop | Called `list_files()` with identical (empty) args 15 times in a row, byte-identical result every time. No other tool ever called, no `finish`. Zero adaptation. |
| task_008 / Config A / trial 1 | FAIL | implementation (destructive overwrite), tool (misdirected recovery) | Refactor edit deleted a pre-existing `render_list` function the task explicitly said didn't need to change (confirmed against the real starting repo and task description). On hitting the resulting ImportError, tried writing directly to the hidden test path (blocked), then repeatedly rewrote a harmless decoy test file in its own workspace instead of fixing its own code. |
| task_008 / Config B / trial 1 | FAIL | implementation (destructive overwrite), loop | Same destructive deletion of `render_list` as the Config A trial above, with the full original file already in context from the start. No test-file detour this time -- just repeated rewrites of the same file, never restoring the missing function. |
| task_004 / Config A / trial 1 | FAIL | infra (not a competence failure) | A provider timeout ended the run at iteration 4, mid-recovery, via the harness's own graceful-degradation handling. Counted as FAIL but not informative about agent competence -- local-inference flakiness, not reasoning. |
| task_019 / Config B / trial 1 | FAIL | implementation (destructive overwrite), loop | Same shape again: a refactor edit introduced an ImportError for a missing function the hidden tests expected, and the agent never recovered for the rest of the budget. |

The task_005 pair above (identical destructive-overwrite mistake under both configs, self-corrected under A within its context budget, stuck under B once its larger upfront prompt pushed the conversation near the local model's real 4096-token context window) is the most direct evidence in this whole project that Context B is not simply 'more information, therefore better' -- it also structurally costs more of a fixed context budget per turn, a genuine confound in the A/B comparison worth stating explicitly rather than folding silently into the headline result.

## Example traces (verbatim, pulled from the real trace files)

**task_005 / Config B / trial 1 -- the stuck-loop mechanism, in the model's own words:**

- iteration 9 (`tokens_in=2455`): `"thought": "The tests are failing because the `most_recent` method is returning the notes in the wrong order. I need to fix the method to return the notes in the correct order.",`
- iteration 13 (`tokens_in=4036`): `"thought": "The tests are failing because the `most_recent` method is returning the notes in the wrong order. I need to fix the method to return the notes in the correct order.",`
- iteration 15 (`tokens_in=4034`): `"thought": "The tests are failing because the `most_recent` method is returning the notes in the wrong order. I need to fix the method to return the notes in the correct order.",`

  Same stated diagnosis three times, ~4,000 input tokens deep into a 4096-token context window, the fix never lands.

**task_014 / Config A / trial 2 -- the starkest loop failure in the benchmark:**

  All 15 iterations: `['list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files', 'list_files']`

**task_008 -- the same destructive refactor, both configs, verbatim diff:**

```diff
-    lines = [f"# {note.title}", "", note.body]
+    lines = [_format_header(note), "", note.body]
```
  ...applied correctly in both runs, but the accompanying full-file rewrite in both runs also silently dropped the pre-existing `render_list` function, which the task description explicitly said didn't need to change -- caught by the hidden test's ImportError, not by the agent.
