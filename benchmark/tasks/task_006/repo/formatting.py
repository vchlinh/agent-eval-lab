"""Rendering helpers for turning Notes into human-readable text."""


def _format_header(note):
    return f"# {note.title}"


def render_note(note):
    """Render a note as a multi-line block: header, body, and tags (if any)."""
    lines = [_format_header(note), "", note.body]
    if note.tags:
        lines.append("")
        lines.append("Tags: " + ", ".join(note.tags))
    return "\n".join(lines)


def render_summary(note, max_len=50):
    """Render a one-line summary: "<header> - <body, truncated to max_len>"."""
    header = _format_header(note)
    if len(note.body) < max_len:
        text = note.body
    else:
        text = note.body[:max_len] + "..."
    return f"{header} - {text}"


def render_list(notes):
    """Render multiple notes, separated by a horizontal rule."""
    return "\n---\n".join(render_note(n) for n in notes)
