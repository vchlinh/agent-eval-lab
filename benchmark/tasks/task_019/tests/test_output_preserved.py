from expenses import ExpenseTracker
from budget import format_single_category, format_budget_report


def test_format_single_category_under_budget():
    t = ExpenseTracker()
    t.add(50, "food")
    assert format_single_category(t, "food", 100) == "food: 50.00 / 100.00 (ok)"


def test_format_single_category_over_budget():
    t = ExpenseTracker()
    t.add(150, "food")
    assert format_single_category(t, "food", 100) == "food: 150.00 / 100.00 (OVER)"


def test_format_single_category_exactly_at_limit_is_ok():
    t = ExpenseTracker()
    t.add(100, "food")
    assert format_single_category(t, "food", 100) == "food: 100.00 / 100.00 (ok)"


def test_format_budget_report_multiple_categories_in_order():
    t = ExpenseTracker()
    t.add(50, "food")
    t.add(150, "rent")
    limits = {"food": 100, "rent": 100}
    expected = "food: 50.00 / 100.00 (ok)\nrent: 150.00 / 100.00 (OVER)"
    assert format_budget_report(t, limits) == expected


def test_format_budget_report_empty_limits_is_empty_string():
    t = ExpenseTracker()
    assert format_budget_report(t, {}) == ""
