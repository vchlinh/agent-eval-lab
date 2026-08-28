from expenses import ExpenseTracker
from budget import categories_over_budget


def make_tracker():
    t = ExpenseTracker()
    t.add(120, "food")
    t.add(50, "rent")
    t.add(80, "fun")
    return t


def test_returns_only_over_budget_categories():
    t = make_tracker()
    limits = {"food": 100, "rent": 500, "fun": 50}
    assert categories_over_budget(t, limits) == ["food", "fun"]


def test_exactly_at_limit_is_not_over():
    t = ExpenseTracker()
    t.add(100, "food")
    limits = {"food": 100}
    assert categories_over_budget(t, limits) == []


def test_none_over_budget_returns_empty():
    t = make_tracker()
    limits = {"food": 500, "rent": 500, "fun": 500}
    assert categories_over_budget(t, limits) == []


def test_results_are_alphabetically_sorted_regardless_of_dict_order():
    t = ExpenseTracker()
    t.add(999, "zebra")
    t.add(999, "apple")
    limits = {"zebra": 1, "apple": 1}
    assert categories_over_budget(t, limits) == ["apple", "zebra"]


def test_category_with_no_expenses_is_not_over():
    t = ExpenseTracker()
    limits = {"unused": 10}
    assert categories_over_budget(t, limits) == []


def test_unrelated_functions_still_work():
    """Adding categories_over_budget() shouldn't disturb remaining/is_over_budget."""
    from budget import remaining, is_over_budget
    t = make_tracker()
    assert remaining(t, "food", 100) == -20
    assert is_over_budget(t, "food", 100) is True
    assert is_over_budget(t, "rent", 500) is False
