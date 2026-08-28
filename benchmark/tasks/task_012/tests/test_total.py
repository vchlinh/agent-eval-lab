from expenses import ExpenseTracker


def test_total_sums_amounts():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(25, "rent")
    t.add(5, "food")
    assert t.total() == 40


def test_total_single_expense():
    t = ExpenseTracker()
    t.add(42, "food")
    assert t.total() == 42


def test_total_empty_tracker_is_zero():
    t = ExpenseTracker()
    assert t.total() == 0


def test_total_after_delete_excludes_removed_expense():
    t = ExpenseTracker()
    a = t.add(10, "food")
    t.add(20, "rent")
    t.delete(a.id)
    assert t.total() == 20


def test_unrelated_methods_still_work():
    """Fixing total() shouldn't disturb the rest of ExpenseTracker."""
    t = ExpenseTracker()
    e = t.add(10, "food", date="2026-08-01")
    assert t.get(e.id).amount == 10
    assert t.by_category("food") == [e]
    assert t.total_by_category("food") == 10
    assert t.largest(1)[0].id == e.id
