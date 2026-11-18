"""Tests for detectmatelibrary.utils.key_extractor."""
from detectmatelibrary.utils.key_extractor import KeyExtractor


def test_finds_a_key_that_contains_the_substring_in_any_case():
    assert KeyExtractor("time").extract({"Timestamp": "t", "message": "m"}) == "t"


def test_finds_a_nested_key_and_reports_its_path():
    log = {"meta": [{"host": "a"}, {"event_time": "t"}]}
    assert KeyExtractor("time").extract(log, return_path=True) == ("t", ["meta", 1, "event_time"])


def test_a_top_level_key_is_found_before_a_nested_one():
    assert KeyExtractor("time").extract({"inner": {"time": "nested"}, "time": "top"}) == "top"


def test_missing_key_gives_none():
    extractor = KeyExtractor("time")
    assert extractor.extract({"message": "m"}) is None
    assert extractor.extract({"message": "m"}, return_path=True) == (None, None)


def test_delete_removes_the_field_from_a_dict_and_from_a_list():
    log = {"time": "t", "message": "m"}
    assert KeyExtractor("time").extract(log, delete=True) == "t"
    assert log == {"message": "m"}

    nested = {"items": [{"time": "t"}, "x"]}
    assert KeyExtractor("time").extract(nested, delete=True) == "t"
    assert nested == {"items": [{}, "x"]}


def test_the_found_path_is_reused_for_the_next_log():
    extractor = KeyExtractor("time")
    extractor.extract({"a": {"time": "first"}})
    # the cached path wins although this log also has a top-level match
    assert extractor.extract({"a": {"time": "second"}, "time": "top"}) == "second"


def test_a_changed_structure_falls_back_to_a_new_search():
    extractor = KeyExtractor("time")
    extractor.extract({"a": {"time": "first"}})
    assert extractor.extract({"b": [{"time": "moved"}]}, return_path=True) == ("moved", ["b", 0, "time"])
