from datetime import datetime

test_time = False


def time_test_mode(new_value: bool = True) -> None:
    global test_time
    test_time = new_value


def get_timestamp() -> int:
    if test_time:
        return 0

    return int(datetime.now().timestamp())


def replaced_with_sets(d: dict) -> dict:
    new_dict = {}
    for key, value in d.items():
        if isinstance(value, dict):
            # Recursively process nested dicts
            new_dict[key] = replaced_with_sets(value)
        else:
            # Replace innermost (non-dict) values with an empty set
            new_dict[key] = set()
    return new_dict
