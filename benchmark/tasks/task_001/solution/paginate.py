def paginate(items, page_size):
    """Split items into pages of at most page_size items each."""
    pages = []
    for i in range(0, len(items), page_size):
        pages.append(items[i:i + page_size])
    return pages
