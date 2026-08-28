import pytest

from expenses import ExpenseTracker


def test_negative_amount_raises_value_error():
    t = ExpenseTracker()
    with pytest.raises(ValueError):
        t.add(-5, "food")


def test_large_negative_amount_raises_value_error():
    t = ExpenseTracker()
    with pytest.raises(ValueError):
        t.add(-1000, "food")


def test_zero_amount_is_allowed_not_an_error():
    t = ExpenseTracker()
    e = t.add(0, "food")
    assert e.amount == 0


def test_zero_amount_is_stored_and_retrievable():
    t = ExpenseTracker()
    e = t.add(0, "food")
    assert t.get(e.id).amount == 0
    assert e in t.by_category("food")


def test_positive_amount_still_works():
    t = ExpenseTracker()
    e = t.add(25, "food")
    assert e.amount == 25


def test_unrelated_methods_still_work():
    """Fixing amount validation shouldn't disturb the rest of ExpenseTracker."""
    t = ExpenseTracker()
    e = t.add(10, "food", date="2026-08-01")
    assert t.total() == 10
    assert t.total_by_category("food") == 10
    assert t.largest(1)[0].id == e.id
    assert t.monthly_total("2026-08") == 10
