from notes import NoteStore


def test_most_recent_returns_latest_first():
    s = NoteStore()
    s.add("first", "...")
    s.add("second", "...")
    s.add("third", "...")
    result = s.most_recent(2)
    assert [n.title for n in result] == ["third", "second"]


def test_most_recent_one():
    s = NoteStore()
    s.add("first", "...")
    s.add("second", "...")
    result = s.most_recent(1)
    assert [n.title for n in result] == ["second"]


def test_most_recent_n_exceeds_count_returns_all_in_order():
    s = NoteStore()
    s.add("only", "...")
    result = s.most_recent(5)
    assert len(result) == 1
    assert result[0].title == "only"


def test_most_recent_zero_returns_empty():
    s = NoteStore()
    s.add("a", "...")
    assert s.most_recent(0) == []


def test_most_recent_negative_returns_empty():
    s = NoteStore()
    s.add("a", "...")
    assert s.most_recent(-3) == []


def test_most_recent_empty_store():
    s = NoteStore()
    assert s.most_recent(3) == []


def test_unrelated_methods_still_work():
    """Adding most_recent() shouldn't disturb the rest of NoteStore."""
    s = NoteStore()
    n = s.add("Groceries", "milk", tags=["home"])
    assert s.get(n.id).title == "Groceries"
    assert n in s.by_tag("home")
    assert n in s.search("milk")
    s.archive(n.id)
    assert s.active() == []
