"""A tiny expense tracker: record expenses, categorize, summarize."""


class Expense:
    def __init__(self, id, amount, category, description="", date=None):
        self.id = id
        self.amount = amount
        self.category = category
        self.description = description
        self.date = date  # "YYYY-MM-DD" string, or None

    def __repr__(self):
        return f"Expense(id={self.id!r}, amount={self.amount!r}, category={self.category!r})"


class ExpenseTracker:
    """In-memory collection of Expenses, keyed by an auto-incrementing id."""

    def __init__(self):
        self._expenses = {}
        self._next_id = 1

    def add(self, amount, category, description="", date=None):
        """Create and store a new Expense, returning it. `amount` must be >= 0."""
        if amount < 0:
            raise ValueError("amount must be non-negative")
        expense = Expense(self._next_id, amount, category, description, date)
        self._expenses[expense.id] = expense
        self._next_id += 1
        return expense

    def get(self, expense_id):
        return self._expenses.get(expense_id)

    def delete(self, expense_id):
        """Remove the expense with the given id. Returns True if an expense
        was actually removed, False if no expense had that id."""
        if expense_id in self._expenses:
            del self._expenses[expense_id]
            return True
        return False

    def all(self):
        return list(self._expenses.values())

    def total(self):
        return sum(e.amount for e in self._expenses.values())

    def by_category(self, category):
        return [e for e in self._expenses.values() if e.category == category]

    def total_by_category(self, category):
        total = 0
        for e in self._expenses.values():
            if e.category == category:
                total += e.amount
        return total

    def average_by_category(self, category):
        """
        Average expense amount in `category`, or 0.0 if there are no
        expenses in that category (never raises ZeroDivisionError).
        """
        matching = self.by_category(category)
        if not matching:
            return 0.0
        return sum(e.amount for e in matching) / len(matching)

    def largest(self, n):
        """
        Return the `n` largest expenses by amount, descending. Ties are
        broken by insertion order (earlier expense first).

        If `n` exceeds the number of stored expenses, return all of them.
        If `n` <= 0, return an empty list.
        """
        if n <= 0:
            return []
        ordered = sorted(self._expenses.values(), key=lambda e: (-e.amount, e.id))
        return ordered[:n]

    def monthly_total(self, month):
        """
        Sum of expenses whose `date` starts with `month` (e.g. "2026-08"
        matches a date of "2026-08-15"). Expenses with `date=None` are
        excluded.
        """
        return sum(
            e.amount for e in self._expenses.values()
            if e.date is not None and e.date.startswith(month)
        )
