"""
This task asks the agent to WRITE tests, not fix code — so grading can't
just run a fixed hidden test file against a fixed implementation. Instead:

  1. Confirm the agent created the required test file.
  2. Run the agent's test file against the correct `render_note` — it must pass.
  3. Swap in a few plausible-bug mutants of `render_note` one at a time and
     rerun the agent's test file against each — it must FAIL on every one.
     If the agent's tests don't fail on any mutant, they aren't actually
     testing the behavior that matters (e.g. an empty test file, or a test
     that only checks the return type).

`formatting.py` is restored to its original content after every mutant,
so the task's own correctness (unrelated behavior intact) isn't affected
by this file being temporarily rewritten mid-grading.
"""

import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")
AGENT_TEST_FILE = "test_render_note.py"
TARGET_FILE = "formatting.py"

ORIGINAL_FORMATTING = (WORKSPACE / TARGET_FILE).read_text()


def _mutant(old, new):
    assert ORIGINAL_FORMATTING.count(old) == 1, "mutant setup assumption broken"
    return ORIGINAL_FORMATTING.replace(old, new, 1)


MUTANTS = {
    "drops_tags": _mutant(
        '    lines = [_format_header(note), "", note.body]\n'
        "    if note.tags:\n"
        '        lines.append("")\n'
        '        lines.append("Tags: " + ", ".join(note.tags))\n'
        '    return "\\n".join(lines)',
        '    lines = [_format_header(note), "", note.body]\n'
        '    return "\\n".join(lines)',
    ),
    "wrong_tag_separator": _mutant(
        'lines.append("Tags: " + ", ".join(note.tags))',
        'lines.append("Tags: " + " ".join(note.tags))',
    ),
    "no_blank_line_before_body": _mutant(
        '    lines = [_format_header(note), "", note.body]\n'
        "    if note.tags:",
        '    lines = [_format_header(note), note.body]\n'
        "    if note.tags:",
    ),
}


def _run_agent_tests():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", AGENT_TEST_FILE],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
    )
    return result.returncode


def test_agent_created_the_required_test_file():
    assert (WORKSPACE / AGENT_TEST_FILE).is_file(), (
        f"expected the agent to create {AGENT_TEST_FILE} in the repo root"
    )


def test_agent_tests_pass_against_the_correct_implementation():
    assert (WORKSPACE / AGENT_TEST_FILE).is_file(), "no test file to run"
    rc = _run_agent_tests()
    assert rc == 0, "agent's own tests must pass against the correct render_note"


def test_agent_tests_catch_dropped_tags_mutant():
    _assert_catches_mutant("drops_tags")


def test_agent_tests_catch_wrong_separator_mutant():
    _assert_catches_mutant("wrong_tag_separator")


def test_agent_tests_catch_missing_blank_line_mutant():
    _assert_catches_mutant("no_blank_line_before_body")


def _assert_catches_mutant(name):
    target = WORKSPACE / TARGET_FILE
    if not (WORKSPACE / AGENT_TEST_FILE).is_file():
        raise AssertionError("no test file to run")
    try:
        target.write_text(MUTANTS[name])
        rc = _run_agent_tests()
        assert rc != 0, f"agent's tests should fail against mutant '{name}' but passed"
    finally:
        target.write_text(ORIGINAL_FORMATTING)
