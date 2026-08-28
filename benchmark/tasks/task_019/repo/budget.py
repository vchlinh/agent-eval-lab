"""Budget-tracking helpers built on top of an ExpenseTracker."""


def remaining(tracker, category, limit):
    """How much of `limit` is left for `category`, after subtracting what's
    already been spent. Can be negative if over budget."""
    return limit - tracker.total_by_category(category)


def is_over_budget(tracker, category, limit):
    return tracker.total_by_category(category) > limit


def categories_over_budget(tracker, limits):
    """
    `limits` is a dict of category -> limit. Return a sorted list of
    category names (from `limits`) whose spending exceeds their limit.
    """
    return sorted(
        category for category, limit in limits.items()
        if tracker.total_by_category(category) > limit
    )


def format_single_category(tracker, category, limit):
    """Render one category's budget line."""
    spent = tracker.total_by_category(category)
    status = "OVER" if spent > limit else "ok"
    return f"{category}: {spent:.2f} / {limit:.2f} ({status})"


def format_budget_report(tracker, limits):
    """
    `limits` is a dict of category -> limit. Returns a multi-line report,
    one line per category in `limits`, in the order given.
    """
    lines = []
    for category, limit in limits.items():
        spent = tracker.total_by_category(category)
        status = "OVER" if spent > limit else "ok"
        lines.append(f"{category}: {spent:.2f} / {limit:.2f} ({status})")
    return "\n".join(lines)
