from collections import OrderedDict
from collections.abc import Iterator
from typing import List

from .preview_helpers import list_preview_str


class LRUSet:
    """LRU = Least Recently Used.

    A set with a maximum size that evicts the least-recently-used items
    when full.
    """

    def __init__(self, max_size: int):
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self.max_size = max_size
        self._d: OrderedDict[object, None] = OrderedDict()

    def add(self, item: object) -> None:
        # Touch -> mark as most-recent
        if item in self._d:
            self._d.move_to_end(item)
            return

        self._d[item] = None
        if len(self._d) > self.max_size:
            self._d.popitem(last=False)  # evict LRU

    def touch(self, item: object) -> bool:
        """Mark item as most-recent if present.

        Returns True if present.
        """
        if item in self._d:
            self._d.move_to_end(item)
            return True
        return False

    def discard(self, item: object) -> None:
        self._d.pop(item, None)

    def __contains__(self, item: object) -> bool:
        return item in self._d

    def __len__(self) -> int:
        return len(self._d)

    def __iter__(self) -> Iterator[object]:
        return iter(self._d)

    def items_lru_to_mru(self) -> List[object]:
        return list(self._d.keys())

    def __repr__(self) -> str:
        return f"LRUSet({list_preview_str(self._d.keys())})"


# example usage:

# lru = LRUSet(max_size=3)
# lru.add("a")
# lru.add("b")
# lru.add("c")
# print(lru) # LRUSet(['a', 'b', 'c'])
# lru.add("d")
# print(lru) # LRUSet(['b', 'c', 'd'])
