# Incremental RLE implementation.
# https://en.wikipedia.org/wiki/Run-length_encoding

from typing import Generic, Iterable, Iterator, List, Tuple, TypeVar

from .preview_helpers import list_preview_str

T = TypeVar("T")


class RLEList(Generic[T]):
    """List-like container storing data in run-length encoded form."""

    def __init__(self, data: Iterable[T] | None = None):
        self._runs: List[Tuple[T, int]] = []
        self._len: int = 0
        if data is not None:
            for x in data:
                self.append(x)

    def append(self, x: T) -> None:
        if self._runs and self._runs[-1][0] == x:
            v, c = self._runs[-1]
            self._runs[-1] = (v, c + 1)
        else:
            self._runs.append((x, 1))
        self._len += 1

    def extend(self, xs: Iterable[T]) -> None:
        for x in xs:
            self.append(x)

    def __len__(self) -> int:
        return self._len

    def __iter__(self) -> Iterator[T]:
        for v, c in self._runs:
            for _ in range(c):
                yield v

    def runs(self) -> List[Tuple[T, int]]:
        """Return the internal RLE representation."""
        return list(self._runs)

    def __repr__(self) -> str:
        # convert bool to int
        runs_str = list_preview_str(self._runs)
        return f"RLEList(len={self._len}, runs={runs_str})"


# example usage
if __name__ == "__main__":
    r = RLEList[str]()

    r.append("A")
    r.append("A")
    r.append("B")
    r.extend(["B", "B", "C"])

    print(len(r))        # 6
    print(list(r))       # ['A', 'A', 'B', 'B', 'B', 'C']
    print(r.runs())      # [('A', 2), ('B', 3), ('C', 1)]
    print(r)             # RLEList(len=6, runs=[('A', 2), ('B', 3), ('C', 1)])
