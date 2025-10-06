from datetime import datetime


class IDGenerator:
    def __init__(self, start_id: int) -> None:
        self.current_id = start_id - 1

    def __call__(self) -> int:
        self.current_id += 1
        return self.current_id


def current_timestamp() -> int:
    return int(datetime.now().timestamp())
