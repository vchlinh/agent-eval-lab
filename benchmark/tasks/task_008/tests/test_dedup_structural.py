"""
Behavioral golden-output tests alone can't tell a real refactor apart from
"leave the duplication in place" (both produce identical output). This test
adds the one structural check the task description explicitly asks for:
a single shared `_format_header(note)` function that BOTH render_note and
render_summary actually call — verified by monkeypatching it and confirming
both functions' output reflects the patch, not just checking the function
exists.
"""

import formatting
from notes import Note


def test_render_note_and_render_summary_share_one_header_function():
    n = Note(1, "Original", "body")

    assert hasattr(formatting, "_format_header"), (
        "expected a shared header-formatting function named _format_header(note), "
        "as described in the task"
    )
    original = formatting._format_header
    try:
        formatting._format_header = lambda note: "PATCHED-HEADER"
        note_result = formatting.render_note(n)
        summary_result = formatting.render_summary(n)
        assert "PATCHED-HEADER" in note_result, (
            "render_note doesn't call the shared _format_header"
        )
        assert "PATCHED-HEADER" in summary_result, (
            "render_summary doesn't call the shared _format_header "
            "(duplication only partially removed)"
        )
    finally:
        formatting._format_header = original
