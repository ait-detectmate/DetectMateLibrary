import pytest
from tools.workspace.utils import normalize_package_name


@pytest.mark.parametrize("input_name, expected", [
    ("custom-parser", "custom_parser"),
    ("custom.parser", "custom_parser"),
    ("CUSTOM__Thing", "custom_thing"),
    ("a--b..c", "a_b_c"),
])
def test_normalize_package_name_basic_cases(input_name: str, expected: str) -> None:
    assert normalize_package_name(input_name) == expected


@pytest.mark.parametrize("input_name", [
    "_leading", "trailing_", "--both--", "...", "__"
])
def test_normalize_package_name_strips_outer_underscores(input_name: str) -> None:
    result = normalize_package_name(input_name)
    assert not result.startswith("_")
    assert not result.endswith("_")
