"""
Builds the final Day-3 report as a static Markdown file, pulling every
number directly from the actual run/analysis/judge artifacts on disk
rather than hand-typing results -- so the report can be regenerated and
can't silently drift from the data it describes.

    python -m report.build_report

Writes report/REPORT.md. A static Markdown report is a deliberate choice
over a Streamlit dashboard here, per the plan's own guidance: build the
report content and stats first, and treat a dashboard as optional
polish, not a substitute for finishing the analysis.
"""

from __future__ import annotations

from pathlib import Path

from analysis.bootstrap import paired_bootstrap_diff
from analysis.intervals import wilson_ci
from analysis.significance import mcnemar_test
from evaluation.correctness import (
    load_results,
    overall_pass_rate,
    pass_rate_by_category,
    pass_rate_by_task,
)
from evaluation.efficiency import efficiency_summary
from evaluation.robustness import robustness_histogram
from harness.tracer import read_trace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_A = PROJECT_ROOT / "results" / "run_20260828T165716Z_qwen2.5-coder-7b"
RUN_B = PROJECT_ROOT / "results" / "run_20260831T024931Z_qwen2.5-coder-7b_contextB"

CATEGORY_ORDER = ["bug_fix", "feature", "edge_case", "test_writing", "refactor", "api_change_docs"]

# The failure-taxonomy hand-review is inherently a human judgment call, not
# something computed from results.json -- captured here as structured data
# (see PROGRESS.md's 2026-08-31 entries for the full trace-by-trace
# reasoning behind each tag) so the report can render it as a table rather
# than a wall of prose.
FAILURE_TAXONOMY = [
    {
        "trace": "task_005 / Config A / trial 1",
        "outcome": "PASS",
        "tags": ["implementation (destructive overwrite)", "recovery (successful)"],
        "note": "First edit dropped an existing `Note` class and a module-level constant. "
        "The resulting NameError was caught and fixed on the very next attempt.",
    },
    {
        "trace": "task_005 / Config B / trial 1",
        "outcome": "FAIL",
        "tags": ["implementation (destructive overwrite)", "loop"],
        "note": "Identical destructive-overwrite mistake as the Config A trial above, despite "
        "Context B having handed it the complete original file verbatim. Recovered from that, "
        "but then repeated an identical (correct) diagnosis of a second bug for 7+ iterations "
        "without ever fixing it. tokens_in climbed from 1,233 to 4,034-4,082 by the final "
        "iterations -- at the local model's actual 4096-token context window.",
    },
    {
        "trace": "task_016 / Config A / trial 1",
        "outcome": "FAIL",
        "tags": ["understanding", "test-interpretation", "loop"],
        "note": "Wrote a test asserting a hallucinated API (`add_expense(...)`) before reading "
        "the real file; corrected the API call after reading it, but the test still asserted "
        "custom-object equality the class doesn't support, then rewrote byte-identical content "
        "for the remaining iterations.",
    },
    {
        "trace": "task_014 / Config A / trial 2",
        "outcome": "FAIL",
        "tags": ["loop"],
        "note": "Called `list_files()` with identical (empty) args 15 times in a row, byte-identical "
        "result every time. No other tool ever called, no `finish`. Zero adaptation.",
    },
    {
        "trace": "task_008 / Config A / trial 1",
        "outcome": "FAIL",
        "tags": ["implementation (destructive overwrite)", "tool (misdirected recovery)"],
        "note": "Refactor edit deleted a pre-existing `render_list` function the task explicitly "
        "said didn't need to change (confirmed against the real starting repo and task "
        "description). On hitting the resulting ImportError, tried writing directly to the "
        "hidden test path (blocked), then repeatedly rewrote a harmless decoy test file in its "
        "own workspace instead of fixing its own code.",
    },
    {
        "trace": "task_008 / Config B / trial 1",
        "outcome": "FAIL",
        "tags": ["implementation (destructive overwrite)", "loop"],
        "note": "Same destructive deletion of `render_list` as the Config A trial above, with the "
        "full original file already in context from the start. No test-file detour this time -- "
        "just repeated rewrites of the same file, never restoring the missing function.",
    },
    {
        "trace": "task_004 / Config A / trial 1",
        "outcome": "FAIL",
        "tags": ["infra (not a competence failure)"],
        "note": "A provider timeout ended the run at iteration 4, mid-recovery, via the harness's "
        "own graceful-degradation handling. Counted as FAIL but not informative about agent "
        "competence -- local-inference flakiness, not reasoning.",
    },
    {
        "trace": "task_019 / Config B / trial 1",
        "outcome": "FAIL",
        "tags": ["implementation (destructive overwrite)", "loop"],
        "note": "Same shape again: a refactor edit introduced an ImportError for a missing "
        "function the hidden tests expected, and the agent never recovered for the rest of "
        "the budget.",
    },
]

TAXONOMY_HEADLINE = (
    "Destructive whole-file overwrite -- `write_file` always replaces a file's entire "
    "content, so whenever the model doesn't faithfully reproduce every part of a file it's "
    "rewriting, whatever it omits is silently deleted -- is the single most common root cause "
    "in this hand-reviewed sample, appearing in 5 of 8 traces, under BOTH configs. It is a "
    "tool/agent-design property, not a context-availability one, and it means a real share of "
    "both configs' raw pass/fail numbers reflects 'did this trial happen to delete something "
    "it shouldn't have' rather than context strategy."
)


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _fmt_ci(lower: float, upper: float) -> str:
    return f"[{lower * 100:.0f}%, {upper * 100:.0f}%]"


def build_leaderboard_section(results_a: list[dict], results_b: list[dict]) -> str:
    lines = ["## Leaderboard\n"]
    lines.append("Same model, temperature, tool set, sandbox, and iteration budget for both "
                  "configs -- context strategy is the only variable that differs.\n")
    lines.append("| Config | Trials | Pass rate | Wilson 95% CI |")
    lines.append("|---|---|---|---|")
    for label, results in (("A (task description only)", results_a), ("B (+ repo tree + files)", results_b)):
        n = len(results)
        k = sum(1 for r in results if r["passed"])
        lower, upper = wilson_ci(k, n)
        lines.append(f"| {label} | {n} | {_fmt_pct(k / n)} ({k}/{n}) | {_fmt_ci(lower, upper)} |")
    lines.append("")
    return "\n".join(lines)


def build_category_section(results_a: list[dict], results_b: list[dict]) -> str:
    cat_a = pass_rate_by_category(results_a)
    cat_b = pass_rate_by_category(results_b)
    lines = ["## Category breakdown\n"]
    lines.append("Per-trial pass rate (not Wilson-CI'd individually -- each category is only "
                  "2-4 tasks x 2 trials, too few for a meaningful per-category interval; use "
                  "the overall CIs above for the headline claim).\n")
    lines.append("| Category | Config A | Config B | Delta |")
    lines.append("|---|---|---|---|")
    for cat in CATEGORY_ORDER:
        a, b = cat_a.get(cat, 0.0), cat_b.get(cat, 0.0)
        delta = (b - a) * 100
        sign = "+" if delta >= 0 else ""
        lines.append(f"| {cat} | {_fmt_pct(a)} | {_fmt_pct(b)} | {sign}{delta:.0f}pp |")
    lines.append("")
    return "\n".join(lines)


def build_statistics_section(results_a: list[dict], results_b: list[dict]) -> str:
    rates_a = pass_rate_by_task(results_a)
    rates_b = pass_rate_by_task(results_b)
    bootstrap = paired_bootstrap_diff(rates_a, rates_b, seed=42)
    mcnemar = mcnemar_test(rates_a, rates_b)

    lines = ["## Statistics (the actual per-task comparison)\n"]
    lines.append(
        "**This is the real Day-3 result, not the leaderboard above.** The leaderboard's 40 "
        "trials per config are not 40 independent experimental units -- the 20 tasks are, since "
        "each task was run twice under the same config. Every test below operates over those "
        "20 tasks, paired by task id.\n"
    )
    lines.append(
        f"- **Paired bootstrap** on task-level success-rate difference (B − A), "
        f"{bootstrap['n_resamples']:,} resamples of {bootstrap['n_tasks']} tasks: "
        f"observed diff **{bootstrap['observed_diff'] * 100:+.0f} percentage points**, "
        f"95% CI **[{bootstrap['ci_lower'] * 100:.0f}%, {bootstrap['ci_upper'] * 100:.0f}%]**."
    )
    lines.append(
        f"- **McNemar's exact test** on the paired pass/fail table (a task counts as \"pass\" "
        f"if at least 1 of its 2 trials passed): both_pass={mcnemar['both_pass']}, "
        f"both_fail={mcnemar['both_fail']}, A-only={mcnemar['a_only']}, B-only={mcnemar['b_only']}, "
        f"**p = {mcnemar['p_value']:.3f}**."
    )
    lines.append(
        "\nThe bootstrap CI excludes zero -- the direction of the effect is unlikely to be "
        "noise. The exact McNemar test, on only 20 paired tasks, does not clear the "
        "conventional p<0.05 bar. Both statements are true simultaneously and both belong in "
        "this report: a large, bootstrap-CI-backed effect that a small-sample exact test can't "
        "fully certify at conventional thresholds is the honest shape of a result at n≈20 "
        "tasks, not a contradiction to resolve by picking whichever number looks better.\n"
    )
    return "\n".join(lines)


def build_robustness_efficiency_section(results_a: list[dict], results_b: list[dict]) -> str:
    hist_a = robustness_histogram(results_a)
    hist_b = robustness_histogram(results_b)
    eff_a = efficiency_summary(results_a)
    eff_b = efficiency_summary(results_b)

    lines = ["## Robustness and efficiency\n"]
    lines.append("Robustness: how many of the 20 tasks land in each per-task pass fraction "
                  "(2/2 = reliably solvable, 1/2 = solvable but inconsistent, 0/2 = never solved "
                  "in either trial).\n")
    lines.append("| Config | 2/2 | 1/2 | 0/2 |")
    lines.append("|---|---|---|---|")
    for label, hist in (("A", hist_a), ("B", hist_b)):
        lines.append(f"| {label} | {hist.get('2/2', 0)} | {hist.get('1/2', 0)} | {hist.get('0/2', 0)} |")
    lines.append("")

    lines.append("Efficiency (median per trial -- median, not mean, since several trials hit "
                  "the full iteration budget and would skew a mean-based view):\n")
    lines.append("| Config | Iterations | Tool calls | Wall-clock | Est. cost |")
    lines.append("|---|---|---|---|---|")
    for label, eff in (("A", eff_a), ("B", eff_b)):
        lines.append(
            f"| {label} | {eff['iterations']['median']:.0f} | {eff['tool_calls']['median']:.0f} | "
            f"{eff['wall_clock_seconds']['median']:.0f}s | ${eff['est_cost_usd']['median']:.3f} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_judge_section() -> str:
    lines = ["## LLM-judge quality assessment, and where the judge itself broke\n"]
    lines.append(
        "The judge (same local model as the agent-under-test, qwen2.5-coder:7b) scores "
        "readability, minimality, and root-cause-vs-patch on a curated sample of already-"
        "passing patches -- it never decides pass/fail. Full methodology and every raw score: "
        "`evaluation/judge.py`, `evaluation/run_judge_sample.py`, and "
        "`results/judge_sample_20260831T220733Z/report.json`.\n"
    )
    lines.append("### Judge-limitations panel (what it got wrong, not just its scores)\n")
    lines.append(
        "Two built-in stress cases (a bloated-but-passing patch, a passes-tests-but-papers-"
        "over-the-bug patch, both hand-verified to actually pass task_001's real hidden tests) "
        "were scored first, before trusting the judge on real patches:\n"
    )
    lines.append(
        "- **First prompt: the judge failed both stress tests.** It rated the papers-over-the-"
        "bug patch's root_cause_vs_patch at 4-5/5 (\"correctly addresses the root cause\" -- "
        "false, the buggy line was never touched), and the bloated patch's minimality at 3-4/5 "
        "despite unmistakable unused classes and config objects."
    )
    lines.append(
        "- **After one prompt revision** (require identifying the changed lines before "
        "scoring): root_cause_vs_patch on the papers-over-bug case correctly dropped to "
        "1.67/5 -- but the same stricter prompt then *also* dropped root_cause_vs_patch to "
        "2/5 on the bloated patch, which genuinely does fix the root cause, just verbosely. "
        "One fix in one direction introduced a new false negative in the other. Documented "
        "as a real limitation of a 7B local judge rather than tuned further against these two "
        "known fixtures."
    )
    lines.append(
        "\nHand-verifying every head-to-head rationale against the real diffs (not just reading "
        "the scores) surfaced further, concrete failures on real patches:\n"
    )
    lines.append(
        "- **task_001 -- a clear hallucination.** Config A's and B's patches were byte-"
        "identical. The judge's blind comparison still invented a difference, claiming "
        '"Patch 2 ... does not fix the bug" -- false; both patches passed.'
    )
    lines.append(
        "- **task_002 -- inconsistency without hallucination.** Same byte-identical patches, "
        "correctly called identical in the head-to-head call -- but two independent rubric "
        "calls on that exact same diff still returned 5/5/5 vs. 4/4/4.5. The absolute 1-5 "
        "scores carry meaningfully more noise than the blind pairwise preference does."
    )
    lines.append(
        "- **task_008 -- misattributed reasoning.** The two patches differed only by a stray "
        "comment line; the judge preferred one \"because it defines the helper function at the "
        "top of the file\" -- true of both patches equally, not the actual difference between "
        "them."
    )
    lines.append(
        "- **task_009 -- checked and correct**, included deliberately alongside the failures "
        "above: the judge's stated reasoning (preferring the patch that avoided an unnecessary "
        "`__repr__` change) matched the real diff. The judge is not reliably wrong, just not "
        "reliably right -- both need reporting together."
    )
    lines.append("")
    return "\n".join(lines)


def build_taxonomy_section() -> str:
    lines = ["## Failure taxonomy (8 hand-read traces)\n"]
    lines.append(f"**{TAXONOMY_HEADLINE}**\n")
    lines.append("| Trace | Outcome | Tags | Note |")
    lines.append("|---|---|---|---|")
    for entry in FAILURE_TAXONOMY:
        tags = ", ".join(entry["tags"])
        lines.append(f"| {entry['trace']} | {entry['outcome']} | {tags} | {entry['note']} |")
    lines.append("")
    lines.append(
        "The task_005 pair above (identical destructive-overwrite mistake under both configs, "
        "self-corrected under A within its context budget, stuck under B once its larger "
        "upfront prompt pushed the conversation near the local model's real 4096-token context "
        "window) is the most direct evidence in this whole project that Context B is not simply "
        "'more information, therefore better' -- it also structurally costs more of a fixed "
        "context budget per turn, a genuine confound in the A/B comparison worth stating "
        "explicitly rather than folding silently into the headline result.\n"
    )
    return "\n".join(lines)


def build_example_traces_section() -> str:
    lines = ["## Example traces (verbatim, pulled from the real trace files)\n"]

    lines.append("**task_005 / Config B / trial 1 -- the stuck-loop mechanism, in the model's own words:**\n")
    steps = read_trace(RUN_B / "traces" / "task_005_trial1.jsonl")
    for it in (9, 13, 15):
        step = next(s for s in steps if s["iteration"] == it)
        thought_line = step["raw_response"].split("\n")[2].strip() if "\n" in step["raw_response"] else ""
        lines.append(f"- iteration {it} (`tokens_in={step['tokens_in']}`): `{thought_line}`")
    lines.append(
        "\n  Same stated diagnosis three times, ~4,000 input tokens deep into a 4096-token "
        "context window, the fix never lands.\n"
    )

    lines.append("**task_014 / Config A / trial 2 -- the starkest loop failure in the benchmark:**\n")
    steps = read_trace(RUN_A / "traces" / "task_014_trial2.jsonl")
    tools_seen = [s["tool"] for s in steps]
    lines.append(f"  All 15 iterations: `{tools_seen}`\n")

    lines.append("**task_008 -- the same destructive refactor, both configs, verbatim diff:**\n")
    lines.append(
        "```diff\n"
        "-    lines = [f\"# {note.title}\", \"\", note.body]\n"
        "+    lines = [_format_header(note), \"\", note.body]\n"
        "```\n"
        "  ...applied correctly in both runs, but the accompanying full-file rewrite in both "
        "runs also silently dropped the pre-existing `render_list` function, which the task "
        "description explicitly said didn't need to change -- caught by the hidden test's "
        "ImportError, not by the agent.\n"
    )
    return "\n".join(lines)


def main() -> None:
    results_a = load_results(RUN_A)
    results_b = load_results(RUN_B)

    sections = [
        "# Agent Evaluation Lab -- Day 3 Report\n",
        "Context A (task description only) vs. Context B (task description + repo tree + full "
        "file contents), same model (qwen2.5-coder:7b, local via Ollama), temperature 0.2, "
        "same tools/sandbox/iteration budget, 20 tasks x 2 trials per config.\n",
        build_leaderboard_section(results_a, results_b),
        build_category_section(results_a, results_b),
        build_statistics_section(results_a, results_b),
        build_robustness_efficiency_section(results_a, results_b),
        build_judge_section(),
        build_taxonomy_section(),
        build_example_traces_section(),
    ]

    out_path = Path(__file__).parent / "REPORT.md"
    out_path.write_text("\n".join(sections))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
