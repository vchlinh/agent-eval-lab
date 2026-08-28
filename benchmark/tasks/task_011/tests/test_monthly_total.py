from expenses import ExpenseTracker


def test_monthly_total_sums_matching_month():
    t = ExpenseTracker()
    t.add(10, "food", date="2026-08-01")
    t.add(20, "food", date="2026-08-15")
    t.add(99, "food", date="2026-09-01")
    assert t.monthly_total("2026-08") == 30


def test_monthly_total_no_matches_returns_zero():
    t = ExpenseTracker()
    t.add(10, "food", date="2026-08-01")
    assert t.monthly_total("2026-01") == 0


def test_monthly_total_excludes_none_dates():
    t = ExpenseTracker()
    t.add(10, "food", date="2026-08-01")
    t.add(50, "food", date=None)
    assert t.monthly_total("2026-08") == 10


def test_monthly_total_empty_tracker():
    t = ExpenseTracker()
    assert t.monthly_total("2026-08") == 0


def test_monthly_total_single_day_boundary():
    t = ExpenseTracker()
    t.add(5, "food", date="2026-08-31")
    t.add(7, "food", date="2026-09-01")
    assert t.monthly_total("2026-08") == 5
    assert t.monthly_total("2026-09") == 7


def test_unrelated_methods_still_work():
    """Fixing monthly_total() shouldn't disturb the rest of ExpenseTracker."""
    t = ExpenseTracker()
    e = t.add(10, "food")
    assert t.get(e.id).amount == 10
    assert t.total() == 10
    assert t.largest(1)[0].id == e.id
