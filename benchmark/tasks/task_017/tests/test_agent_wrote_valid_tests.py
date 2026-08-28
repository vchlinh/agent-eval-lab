"""
Mutation-testing grading for a test_writing task — see task_007/task_016
for the pattern this mirrors.
"""

import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")
AGENT_TEST_FILE = "test_is_over_budget.py"
TARGET_FILE = "budget.py"

ORIGINAL_BUDGET = (WORKSPACE / TARGET_FILE).read_text()


def _mutant(old, new):
    assert ORIGINAL_BUDGET.count(old) == 1, "mutant setup assumption broken"
    return ORIGINAL_BUDGET.replace(old, new, 1)


MUTANTS = {
    "always_false": _mutant(
        "def is_over_budget(tracker, category, limit):\n"
        "    return tracker.total_by_category(category) > limit",
        "def is_over_budget(tracker, category, limit):\n"
        "    return False",
    ),
    "always_true": _mutant(
        "def is_over_budget(tracker, category, limit):\n"
        "    return tracker.total_by_category(category) > limit",
        "def is_over_budget(tracker, category, limit):\n"
        "    return True",
    ),
    "off_by_one": _mutant(
        "return tracker.total_by_category(category) > limit",
        "return tracker.total_by_category(category) >= limit",
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
    assert rc == 0, "agent's own tests must pass against the correct is_over_budget"


def test_agent_tests_catch_always_false_mutant():
    _assert_catches_mutant("always_false")


def test_agent_tests_catch_always_true_mutant():
    _assert_catches_mutant("always_true")


def test_agent_tests_catch_off_by_one_mutant():
    _assert_catches_mutant("off_by_one")


def _assert_catches_mutant(name):
    target = WORKSPACE / TARGET_FILE
    if not (WORKSPACE / AGENT_TEST_FILE).is_file():
        raise AssertionError("no test file to run")
    try:
        target.write_text(MUTANTS[name])
        rc = _run_agent_tests()
        assert rc != 0, f"agent's tests should fail against mutant '{name}' but passed"
    finally:
        target.write_text(ORIGINAL_BUDGET)
