class SimpleIDGenerator:
    def __init__(self, start_id: int, prefix: str = "") -> None:
        self.current_id = start_id - 1
        self.prefix = "" if prefix == "" else prefix + "_"

    def __call__(self) -> str:
        self.current_id += 1
        return f"{self.prefix}{self.current_id}"
