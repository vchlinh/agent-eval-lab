from expenses import ExpenseTracker


def test_unrelated_methods_still_work():
    """Refactoring total_by_category() shouldn't disturb the rest of ExpenseTracker."""
    t = ExpenseTracker()
    e = t.add(10, "food", date="2026-08-01")
    assert t.get(e.id).amount == 10
    assert t.total() == 10
    assert t.by_category("food") == [e]
    assert t.largest(1)[0].id == e.id
    assert t.monthly_total("2026-08") == 10
