class SimpleIDGenerator:
    def __init__(self, start_id: int) -> None:
        self.current_id = start_id - 1

    def __call__(self) -> str:
        self.current_id += 1
        return f"{self.current_id}"
