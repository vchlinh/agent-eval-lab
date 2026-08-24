import itertools

import pytest

from paginate import paginate

CASES = [
    (10, 3),
    (9, 3),
    (7, 3),
    (4, 3),
    (6, 2),
    (5, 1),
    (1, 3),
    (2, 5),
    (0, 3),
]


@pytest.mark.parametrize("length,page_size", CASES)
def test_all_items_preserved_in_order(length, page_size):
    items = list(range(length))
    pages = paginate(items, page_size)
    assert list(itertools.chain.from_iterable(pages)) == items


@pytest.mark.parametrize("length,page_size", CASES)
def test_no_page_exceeds_page_size(length, page_size):
    items = list(range(length))
    pages = paginate(items, page_size)
    assert all(len(page) <= page_size for page in pages)


@pytest.mark.parametrize("length,page_size", CASES)
def test_no_empty_pages(length, page_size):
    items = list(range(length))
    pages = paginate(items, page_size)
    assert all(len(page) > 0 for page in pages)


@pytest.mark.parametrize("length,page_size", CASES)
def test_page_count_matches_expected(length, page_size):
    items = list(range(length))
    pages = paginate(items, page_size)
    expected_count = -(-length // page_size) if length else 0
    assert len(pages) == expected_count


def test_empty_items_returns_no_pages():
    assert paginate([], 3) == []
