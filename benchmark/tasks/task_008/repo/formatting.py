"""Rendering helpers for turning Notes into human-readable text."""


def render_note(note):
    """Render a note as a multi-line block: header, body, and tags (if any)."""
    lines = [f"# {note.title}", "", note.body]
    if note.tags:
        lines.append("")
        lines.append("Tags: " + ", ".join(note.tags))
    return "\n".join(lines)


def render_summary(note, max_len=50):
    """
    Render a one-line summary: "<header> - <body, truncated to max_len>".

    If the body is longer than `max_len`, it's cut to `max_len` characters
    and an ellipsis is appended. A body exactly `max_len` characters long
    is NOT truncated. `max_len` must be positive.
    """
    if max_len <= 0:
        raise ValueError("max_len must be positive")
    header = f"# {note.title}"
    if len(note.body) <= max_len:
        text = note.body
    else:
        text = note.body[:max_len] + "..."
    return f"{header} - {text}"


def render_list(notes):
    """Render multiple notes, separated by a horizontal rule."""
    return "\n---\n".join(render_note(n) for n in notes)
