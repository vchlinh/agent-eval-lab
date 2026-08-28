from notes import NoteStore


def make_store():
    s = NoteStore()
    s.add("Grocery List", "buy Milk and Bread")
    s.add("Meeting Notes", "Discuss BUDGET for Q3")
    s.add("Recipe", "chocolate cake")
    return s


def test_search_matches_title_case_insensitively():
    s = make_store()
    results = s.search("grocery")
    assert len(results) == 1
    assert results[0].title == "Grocery List"


def test_search_matches_body_lowercase_query_against_mixed_case_body():
    s = make_store()
    results = s.search("milk")
    assert any(n.title == "Grocery List" for n in results)


def test_search_matches_uppercase_query_against_lowercase_body():
    s = make_store()
    results = s.search("CAKE")
    assert len(results) == 1
    assert results[0].title == "Recipe"


def test_search_matches_query_against_all_caps_word_in_body():
    s = make_store()
    results = s.search("budget")
    assert len(results) == 1
    assert results[0].title == "Meeting Notes"


def test_search_no_match_returns_empty():
    s = make_store()
    assert s.search("xyz-nomatch") == []


def test_search_exact_case_match_still_works():
    s = make_store()
    results = s.search("Grocery")
    assert len(results) == 1


def test_unrelated_methods_still_work():
    """Fixing search() shouldn't disturb the rest of NoteStore."""
    s = make_store()
    n = s.add("New", "body", tags=["x"])
    assert s.get(n.id).title == "New"
    assert n in s.by_tag("x")
    s.delete(n.id)
    assert s.get(n.id) is None
    assert s.most_recent(1)[0].title == "Recipe"
