"""Tests for detectmatelibrary.utils.preview_helpers."""
from detectmatelibrary.utils.preview_helpers import format_dict_repr, list_preview_str


def test_a_short_list_is_shown_whole():
    assert list_preview_str(["a", "b", "c", "d", "e", "f"]) == ["a", "b", "c", "d", "e", "f"]


def test_a_long_list_shows_three_items_at_each_end():
    assert list_preview_str(range(10)) == [0, 1, 2, "...", 7, 8, 9]


def test_booleans_become_integers_unless_switched_off():
    assert list_preview_str([True, False]) == [1, 0]
    assert list_preview_str([True, False], bool_to_int=False) == [True, False]


def test_format_dict_repr_puts_one_item_per_indented_line():
    assert format_dict_repr({"a": 1, "b": [2]}, indent="  ") == "a: 1\n  b: [2]"
