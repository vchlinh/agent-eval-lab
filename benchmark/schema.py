"""
Task schema: the data model for one benchmark task, plus loading and
validation.

A task lives as a directory:

    benchmark/tasks/<id>/
        task.yaml   - metadata, description, budget, QA checklist
        repo/       - the starting repo the agent sees and edits
        tests/      - hidden tests; never shown to the agent, only
                      dropped into the working copy at grading time
        solution/   - (optional) a reference fix, used to verify the
                      QA checklist during authoring, never shipped to the agent

Ground rule: a task with an incomplete QA checklist must not silently
enter the benchmark. `load_tasks()` filters those out by default.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from pathlib import Path

import yaml

TASK_YAML_FILENAME = "task.yaml"
REPO_DIRNAME = "repo"
TESTS_DIRNAME = "tests"

QA_CHECKLIST_FIELDS = (
    "starting_repo_fails",
    "description_self_sufficient",
    "reference_solution_passes",
    "alternate_solution_passes",
    "unrelated_behavior_intact",
    "tests_not_guessable",
    "tests_catch_incomplete_solution",
    "runs_within_budget",
)


class TaskCategory(str, Enum):
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    EDGE_CASE = "edge_case"
    TEST_WRITING = "test_writing"
    REFACTOR = "refactor"
    API_CHANGE_DOCS = "api_change_docs"


class TaskValidationError(ValueError):
    """A task's directory or task.yaml is structurally invalid."""


@dataclasses.dataclass
class QAChecklist:
    """
    One entry per line of the QA checklist in the skill/plan. A task only
    counts as "in the benchmark" once every field here is True — see
    Task.qa_complete().
    """

    starting_repo_fails: bool = False
    description_self_sufficient: bool = False
    reference_solution_passes: bool = False
    alternate_solution_passes: bool = False
    unrelated_behavior_intact: bool = False
    tests_not_guessable: bool = False
    tests_catch_incomplete_solution: bool = False
    runs_within_budget: bool = False
    notes: str = ""

    @property
    def is_complete(self) -> bool:
        return all(getattr(self, field) for field in QA_CHECKLIST_FIELDS)

    def missing(self) -> list[str]:
        return [field for field in QA_CHECKLIST_FIELDS if not getattr(self, field)]

    @classmethod
    def from_dict(cls, data: dict) -> "QAChecklist":
        unknown = set(data) - set(QA_CHECKLIST_FIELDS) - {"notes"}
        if unknown:
            raise TaskValidationError(f"qa: unknown field(s) {sorted(unknown)}")
        return cls(**data)


@dataclasses.dataclass
class Budget:
    """Resource limits for one run of one task."""

    max_iterations: int = 15
    timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(**data)


@dataclasses.dataclass
class Task:
    id: str
    title: str
    category: TaskCategory
    description: str
    budget: Budget
    qa: QAChecklist
    task_dir: Path
    test_command: list[str] = dataclasses.field(default_factory=lambda: ["pytest", "-q"])

    @property
    def repo_dir(self) -> Path:
        return self.task_dir / REPO_DIRNAME

    @property
    def tests_dir(self) -> Path:
        return self.task_dir / TESTS_DIRNAME

    @property
    def qa_complete(self) -> bool:
        return self.qa.is_complete

    def validate(self) -> None:
        """Structural checks that don't require running anything."""
        problems = []

        if not self.repo_dir.is_dir():
            problems.append(f"missing {REPO_DIRNAME}/ directory")
        if not self.tests_dir.is_dir():
            problems.append(f"missing {TESTS_DIRNAME}/ directory")
        elif not any(self.tests_dir.glob("test_*.py")):
            problems.append(f"{TESTS_DIRNAME}/ has no test_*.py files")
        if not self.description.strip():
            problems.append("description is empty")

        if problems:
            raise TaskValidationError(f"task '{self.id}': " + "; ".join(problems))


def load_task(task_dir: Path) -> Task:
    """Load and structurally validate a single task from its directory."""
    task_dir = Path(task_dir)
    yaml_path = task_dir / TASK_YAML_FILENAME
    if not yaml_path.is_file():
        raise TaskValidationError(f"{task_dir}: missing {TASK_YAML_FILENAME}")

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    try:
        task = Task(
            id=data["id"],
            title=data["title"],
            category=TaskCategory(data["category"]),
            description=data["description"],
            budget=Budget.from_dict(data.get("budget", {})),
            qa=QAChecklist.from_dict(data.get("qa", {})),
            task_dir=task_dir,
            test_command=data.get("test_command", ["pytest", "-q"]),
        )
    except KeyError as e:
        raise TaskValidationError(f"{task_dir}: missing required field {e}") from e
    except ValueError as e:
        raise TaskValidationError(f"{task_dir}: {e}") from e

    if task.id != task_dir.name:
        raise TaskValidationError(
            f"{task_dir}: task.yaml id '{task.id}' doesn't match directory name"
        )

    task.validate()
    return task


def load_tasks(tasks_root: Path, include_incomplete: bool = False) -> list[Task]:
    """
    Load every task under `tasks_root`. By default, tasks whose QA
    checklist isn't fully checked off are skipped (with a warning) rather
    than silently entering the benchmark — an unvetted task corrupts every
    downstream number.
    """
    tasks_root = Path(tasks_root)
    tasks = []
    for task_dir in sorted(p for p in tasks_root.iterdir() if p.is_dir()):
        if not (task_dir / TASK_YAML_FILENAME).is_file():
            continue
        task = load_task(task_dir)
        if not task.qa_complete and not include_incomplete:
            print(
                f"[schema] skipping '{task.id}': QA checklist incomplete "
                f"(missing: {', '.join(task.qa.missing())})"
            )
            continue
        tasks.append(task)
    return tasks
