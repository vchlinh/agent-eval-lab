"""
Mutation-testing grading for a test_writing task — see task_007's hidden
tests for the pattern this mirrors. The deliverable is test code, so
grading (1) checks the agent created the required file, (2) runs it
against the real by_category (must pass), (3) swaps in mutants of
by_category one at a time and reruns the agent's tests against each
(must fail on every one, or the tests aren't testing real behavior).
expenses.py is restored after each mutant.
"""

import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")
AGENT_TEST_FILE = "test_by_category.py"
TARGET_FILE = "expenses.py"

ORIGINAL_EXPENSES = (WORKSPACE / TARGET_FILE).read_text()


def _mutant(old, new):
    assert ORIGINAL_EXPENSES.count(old) == 1, "mutant setup assumption broken"
    return ORIGINAL_EXPENSES.replace(old, new, 1)


MUTANTS = {
    "matches_all": _mutant(
        "    def by_category(self, category):\n"
        "        return [e for e in self._expenses.values() if e.category == category]",
        "    def by_category(self, category):\n"
        "        return [e for e in self._expenses.values()]",
    ),
    "wrong_field": _mutant(
        "if e.category == category",
        "if e.description == category",
    ),
    "empty_always": _mutant(
        "    def by_category(self, category):\n"
        "        return [e for e in self._expenses.values() if e.category == category]",
        "    def by_category(self, category):\n"
        "        return []",
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
    assert rc == 0, "agent's own tests must pass against the correct by_category"


def test_agent_tests_catch_matches_all_mutant():
    _assert_catches_mutant("matches_all")


def test_agent_tests_catch_wrong_field_mutant():
    _assert_catches_mutant("wrong_field")


def test_agent_tests_catch_empty_always_mutant():
    _assert_catches_mutant("empty_always")


def _assert_catches_mutant(name):
    target = WORKSPACE / TARGET_FILE
    if not (WORKSPACE / AGENT_TEST_FILE).is_file():
        raise AssertionError("no test file to run")
    try:
        target.write_text(MUTANTS[name])
        rc = _run_agent_tests()
        assert rc != 0, f"agent's tests should fail against mutant '{name}' but passed"
    finally:
        target.write_text(ORIGINAL_EXPENSES)
