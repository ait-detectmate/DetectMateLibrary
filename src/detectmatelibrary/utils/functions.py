from typing import Any, Iterable


def replaced_with_objects(d: dict, object_type: Any = set) -> dict:
    """Replace the innermost values of a nested dictionary with instances of a
    specified object type."""
    new_dict = {}
    for key, value in d.items():
        if isinstance(value, dict):
            # Recursively process nested dicts
            new_dict[key] = replaced_with_objects(value, object_type)
        else:
            # Replace innermost (non-dict) values with an empty set
            new_dict[key] = object_type()
    return new_dict


def sorted_int_str(x: Iterable) -> list:
    return sorted(x, key=lambda x: (isinstance(x, str), str(x)))
