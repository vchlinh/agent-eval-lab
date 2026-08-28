"""A tiny note-taking library: store notes, tag them, search and archive them."""

VALID_PRIORITIES = ("low", "normal", "high")


class Note:
    def __init__(self, id, title, body, tags=None, priority="normal"):
        self.id = id
        self.title = title
        self.body = body
        self.tags = list(tags) if tags else []
        self.priority = priority
        self.archived = False

    def __repr__(self):
        return f"Note(id={self.id!r}, title={self.title!r})"


class NoteStore:
    """In-memory collection of Notes, keyed by an auto-incrementing id."""

    def __init__(self):
        self._notes = {}
        self._next_id = 1

    def add(self, title, body, tags=None, priority="normal"):
        """
        Create and store a new Note, returning it.

        `priority` must be one of "low", "normal", or "high"; anything
        else raises ValueError.
        """
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"invalid priority: {priority!r}")
        note = Note(self._next_id, title, body, tags, priority)
        self._notes[note.id] = note
        self._next_id += 1
        return note

    def get(self, note_id):
        return self._notes.get(note_id)

    def delete(self, note_id):
        self._notes.pop(note_id, None)

    def all(self):
        return list(self._notes.values())

    def search(self, query):
        """Return notes whose title or body contains `query`."""
        return [
            n for n in self._notes.values()
            if query in n.title or query in n.body
        ]

    def by_tag(self, tag):
        return [n for n in self._notes.values() if tag in n.tags]

    def archive(self, note_id):
        note = self._notes.get(note_id)
        if note:
            note.archived = True

    def active(self):
        return [n for n in self._notes.values() if not n.archived]

    def most_recent(self, n):
        """
        Return the `n` most recently added notes, most recent first.

        If `n` exceeds the number of stored notes, return all of them.
        If `n` <= 0, return an empty list.
        """
        if n <= 0:
            return []
        ordered = sorted(self._notes.values(), key=lambda note: note.id, reverse=True)
        return ordered[:n]
