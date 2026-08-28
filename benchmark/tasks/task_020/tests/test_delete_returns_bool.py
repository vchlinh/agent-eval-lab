from expenses import ExpenseTracker


def test_delete_existing_expense_returns_true():
    t = ExpenseTracker()
    e = t.add(10, "food")
    assert t.delete(e.id) is True


def test_delete_existing_expense_actually_removes_it():
    t = ExpenseTracker()
    e = t.add(10, "food")
    t.delete(e.id)
    assert t.get(e.id) is None


def test_delete_nonexistent_expense_returns_false():
    t = ExpenseTracker()
    assert t.delete(999) is False


def test_delete_already_deleted_expense_returns_false_second_time():
    t = ExpenseTracker()
    e = t.add(10, "food")
    assert t.delete(e.id) is True
    assert t.delete(e.id) is False


def test_unrelated_methods_still_work():
    """Changing delete()'s return value shouldn't disturb the rest of ExpenseTracker."""
    t = ExpenseTracker()
    e = t.add(10, "food", date="2026-08-01")
    assert t.get(e.id).amount == 10
    assert t.total() == 10
    assert t.by_category("food") == [e]
    assert t.largest(1)[0].id == e.id
