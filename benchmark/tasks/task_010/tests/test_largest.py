from expenses import ExpenseTracker


def test_largest_returns_biggest_first():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(50, "rent")
    t.add(30, "food")
    result = t.largest(2)
    assert [e.amount for e in result] == [50, 30]


def test_largest_one():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(50, "rent")
    result = t.largest(1)
    assert [e.amount for e in result] == [50]


def test_largest_ties_broken_by_insertion_order():
    t = ExpenseTracker()
    first = t.add(20, "food")
    second = t.add(20, "rent")
    result = t.largest(2)
    assert [e.id for e in result] == [first.id, second.id]


def test_largest_n_exceeds_count_returns_all_descending():
    t = ExpenseTracker()
    t.add(5, "food")
    t.add(15, "rent")
    result = t.largest(10)
    assert [e.amount for e in result] == [15, 5]


def test_largest_zero_returns_empty():
    t = ExpenseTracker()
    t.add(10, "food")
    assert t.largest(0) == []


def test_largest_negative_returns_empty():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(20, "rent")
    t.add(30, "food")
    assert t.largest(-2) == []


def test_largest_empty_tracker():
    t = ExpenseTracker()
    assert t.largest(3) == []


def test_unrelated_methods_still_work():
    """Fixing largest() shouldn't disturb the rest of ExpenseTracker."""
    t = ExpenseTracker()
    e = t.add(10, "food", date="2026-08-01")
    assert t.get(e.id).amount == 10
    assert t.total() == 10
    assert e in t.by_category("food")
    assert t.total_by_category("food") == 10
