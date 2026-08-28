import pytest

from notes import NoteStore


def test_add_without_priority_defaults_to_normal():
    s = NoteStore()
    n = s.add("Title", "body")
    assert n.priority == "normal"


def test_add_with_valid_priority_low():
    s = NoteStore()
    n = s.add("Title", "body", priority="low")
    assert n.priority == "low"


def test_add_with_valid_priority_high():
    s = NoteStore()
    n = s.add("Title", "body", tags=["x"], priority="high")
    assert n.priority == "high"
    assert n.tags == ["x"]


def test_add_with_invalid_priority_raises_value_error():
    s = NoteStore()
    with pytest.raises(ValueError):
        s.add("Title", "body", priority="urgent")


def test_add_backward_compatible_positional_and_keyword_args_still_work():
    s = NoteStore()
    n = s.add("Title", "body", ["tag1", "tag2"])
    assert n.title == "Title"
    assert n.tags == ["tag1", "tag2"]
    assert n.priority == "normal"


def test_stored_note_retrievable_with_priority_intact():
    s = NoteStore()
    added = s.add("Title", "body", priority="high")
    fetched = s.get(added.id)
    assert fetched.priority == "high"


def test_unrelated_methods_still_work():
    """Adding the priority param shouldn't disturb the rest of NoteStore."""
    s = NoteStore()
    n = s.add("Title", "body milk", tags=["home"])
    assert n in s.by_tag("home")
    assert n in s.search("milk")
    s.archive(n.id)
    assert s.active() == []
    assert s.most_recent(1)[0].id == n.id
