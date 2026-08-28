import pytest

from notes import Note
from formatting import render_summary


def make_note(body):
    return Note(1, "Title", body)


def test_body_shorter_than_max_len_not_truncated():
    n = make_note("short")
    assert render_summary(n, max_len=50) == "# Title - short"


def test_body_exactly_max_len_not_truncated():
    n = make_note("x" * 10)
    result = render_summary(n, max_len=10)
    assert result == "# Title - " + "x" * 10
    assert "..." not in result


def test_body_one_char_longer_than_max_len_is_truncated():
    n = make_note("x" * 11)
    result = render_summary(n, max_len=10)
    assert result == "# Title - " + "x" * 10 + "..."


def test_body_much_longer_than_max_len_is_truncated():
    n = make_note("x" * 15)
    result = render_summary(n, max_len=10)
    assert result == "# Title - " + "x" * 10 + "..."


def test_max_len_zero_raises_value_error():
    n = make_note("abc")
    with pytest.raises(ValueError):
        render_summary(n, max_len=0)


def test_max_len_negative_raises_value_error():
    n = make_note("abc")
    with pytest.raises(ValueError):
        render_summary(n, max_len=-5)


def test_unrelated_rendering_functions_still_work():
    """Fixing render_summary() shouldn't disturb render_note/render_list."""
    from formatting import render_note, render_list

    n1 = make_note("hello")
    n1.tags = ["x"]
    assert render_note(n1) == "# Title\n\nhello\n\nTags: x"
    n2 = make_note("world")
    assert render_list([n1, n2]) == render_note(n1) + "\n---\n" + render_note(n2)
