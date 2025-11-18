from datetime import datetime

test_time = False


def time_test_mode(new_value: bool = True) -> None:
    global test_time
    test_time = new_value


def get_timestamp() -> int:
    if test_time:
        return 0

    return int(datetime.now().timestamp())
