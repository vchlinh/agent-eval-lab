from expenses import ExpenseTracker


def test_average_by_category_basic():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(20, "food")
    t.add(30, "food")
    assert t.average_by_category("food") == 20


def test_average_by_category_single_expense():
    t = ExpenseTracker()
    t.add(42, "rent")
    assert t.average_by_category("rent") == 42


def test_average_by_category_ignores_other_categories():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(1000, "rent")
    assert t.average_by_category("food") == 10


def test_average_by_category_no_expenses_returns_zero():
    t = ExpenseTracker()
    t.add(10, "food")
    assert t.average_by_category("rent") == 0.0


def test_average_by_category_empty_tracker_returns_zero():
    t = ExpenseTracker()
    assert t.average_by_category("food") == 0.0


def test_unrelated_methods_still_work():
    """Adding average_by_category() shouldn't disturb the rest of ExpenseTracker."""
    t = ExpenseTracker()
    e = t.add(10, "food", date="2026-08-01")
    assert t.get(e.id).amount == 10
    assert t.total() == 10
    assert t.largest(1)[0].id == e.id
    assert t.monthly_total("2026-08") == 10
