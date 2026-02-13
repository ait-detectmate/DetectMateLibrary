from typing import Any, Dict


def list_preview_str(listlike: Any, bool_to_int: bool = True) -> list[Any]:
    """Show a preview of a listlike sequence."""
    series_start = list(listlike)[:3]
    if len(listlike) > 6:
        series_end = list(listlike)[-3:]
        series_preview = series_start + ["..."] + series_end
    else:
        series_preview = list(listlike)
    if bool_to_int:
        series_preview = [int(x) if isinstance(x, bool) else x for x in series_preview]
    return series_preview


def format_dict_repr(items: Dict[str, Any], indent: str = "\t") -> str:
    """Format a dictionary as a multiline string with indentation."""
    return f"\n{indent}".join(f"{name}: {value}" for name, value in items.items())
