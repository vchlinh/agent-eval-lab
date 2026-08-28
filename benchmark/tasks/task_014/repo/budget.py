"""Budget-tracking helpers built on top of an ExpenseTracker."""


def remaining(tracker, category, limit):
    """How much of `limit` is left for `category`, after subtracting what's
    already been spent. Can be negative if over budget."""
    return limit - tracker.total_by_category(category)


def is_over_budget(tracker, category, limit):
    return tracker.total_by_category(category) > limit


def _format_line(category, spent, limit):
    status = "OVER" if spent > limit else "ok"
    return f"{category}: {spent:.2f} / {limit:.2f} ({status})"


def format_single_category(tracker, category, limit):
    """Render one category's budget line."""
    return _format_line(category, tracker.total_by_category(category), limit)


def format_budget_report(tracker, limits):
    """
    `limits` is a dict of category -> limit. Returns a multi-line report,
    one line per category in `limits`, in the order given.
    """
    lines = [
        _format_line(category, tracker.total_by_category(category), limit)
        for category, limit in limits.items()
    ]
    return "\n".join(lines)
