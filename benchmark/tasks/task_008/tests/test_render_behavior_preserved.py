from notes import Note
from formatting import render_note, render_summary, render_list


def test_render_note_no_tags():
    n = Note(1, "Groceries", "milk, bread")
    assert render_note(n) == "# Groceries\n\nmilk, bread"


def test_render_note_with_tags():
    n = Note(1, "Groceries", "milk, bread", tags=["home", "urgent"])
    assert render_note(n) == "# Groceries\n\nmilk, bread\n\nTags: home, urgent"


def test_render_note_empty_body():
    n = Note(1, "Empty", "")
    assert render_note(n) == "# Empty\n\n"


def test_render_summary_short_body():
    n = Note(1, "Title", "short body")
    assert render_summary(n, max_len=50) == "# Title - short body"


def test_render_summary_truncates_long_body():
    n = Note(1, "Title", "x" * 20)
    assert render_summary(n, max_len=10) == "# Title - " + "x" * 10 + "..."


def test_render_summary_boundary_not_truncated():
    n = Note(1, "Title", "x" * 10)
    result = render_summary(n, max_len=10)
    assert result == "# Title - " + "x" * 10
    assert "..." not in result


def test_render_list_joins_with_separator():
    notes = [Note(1, "A", "a-body"), Note(2, "B", "b-body")]
    assert render_list(notes) == "# A\n\na-body\n---\n# B\n\nb-body"


def test_render_list_single_note():
    notes = [Note(1, "Solo", "only one")]
    assert render_list(notes) == render_note(notes[0])
