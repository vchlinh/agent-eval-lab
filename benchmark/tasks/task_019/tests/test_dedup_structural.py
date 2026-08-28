import budget
from expenses import ExpenseTracker


def test_format_functions_share_one_line_formatter():
    t = ExpenseTracker()
    t.add(10, "food")

    assert hasattr(budget, "_format_line"), (
        "expected a shared line-formatting function named "
        "_format_line(category, spent, limit), as described in the task"
    )
    original = budget._format_line
    try:
        budget._format_line = lambda category, spent, limit: "PATCHED-LINE"
        single_result = budget.format_single_category(t, "food", 100)
        report_result = budget.format_budget_report(t, {"food": 100})
        assert single_result == "PATCHED-LINE", (
            "format_single_category doesn't call the shared _format_line"
        )
        assert report_result == "PATCHED-LINE", (
            "format_budget_report doesn't call the shared _format_line "
            "(duplication only partially removed)"
        )
    finally:
        budget._format_line = original
