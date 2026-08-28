from expenses import Expense, ExpenseTracker


def test_total_by_category_delegates_to_by_category():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(20, "food")

    fake_expenses = [Expense(999, 1000, "food"), Expense(998, 2000, "food")]
    original = ExpenseTracker.by_category
    try:
        ExpenseTracker.by_category = lambda self, category: fake_expenses
        assert t.total_by_category("food") == 3000, (
            "total_by_category doesn't call by_category() — it must delegate "
            "to it instead of independently filtering self._expenses"
        )
    finally:
        ExpenseTracker.by_category = original


def test_total_by_category_correct_on_real_data():
    t = ExpenseTracker()
    t.add(10, "food")
    t.add(25, "rent")
    t.add(5, "food")
    assert t.total_by_category("food") == 15
    assert t.total_by_category("rent") == 25


def test_total_by_category_no_matches_is_zero():
    t = ExpenseTracker()
    t.add(10, "food")
    assert t.total_by_category("rent") == 0
