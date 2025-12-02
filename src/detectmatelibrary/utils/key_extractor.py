from collections.abc import Mapping, Sequence
from typing import Any


class KeyExtractor:
    """Efficient extractor for a key in nested dict/list JSON-like objects.

    Caches the path of the first occurrence to speed up future lookups.
    """
    def __init__(self, key_substr: str = "time") -> None:
        self.key_substr = key_substr.lower()
        self._cached_path: list[str | int] | None = None  # list of keys/indices

    def _get_by_path(self, obj: dict[str, Any], path: list[str | int]) -> Any:
        """Follow the cached path in the given object."""
        cur = obj
        for step in path:
            cur = cur[step]  # type: ignore[index]
        return cur

    def _find_path(self, root: dict[str, Any]) -> list[str | int] | None:
        """Iteratively search for first key containing key_substr.

        Returns the path as a list of keys/indices, or None if not
        found.
        """
        stack: list[tuple[Any, list[str | int]]] = [(root, [])]
        while stack:
            current, path = stack.pop()
            if isinstance(current, Mapping):
                for k, v in current.items():
                    if self.key_substr in str(k).lower():
                        # path to the VALUE of this key
                        return path + [k]
                    stack.append((v, path + [k]))
            elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
                for idx, item in enumerate(current):
                    stack.append((item, path + [idx]))
        return None

    def _del_by_path(self, obj: dict[str, Any], path: list[str | int]) -> None:
        """Delete the value at the given path from obj.

        Modifies obj in place.
        """
        if not path:
            return

        # Walk to parent container
        cur = obj
        for step in path[:-1]:
            cur = cur[step]  # type: ignore[index]

        last = path[-1]

        if isinstance(cur, Mapping):
            # delete dict key
            cur.pop(last, None)  # type: ignore[arg-type]
        elif isinstance(cur, Sequence) and not isinstance(cur, (str, bytes, bytearray)):
            # delete list/tuple index
            try:
                del cur[last]
            except (IndexError, TypeError):
                pass

    def extract(
        self, obj: dict[str, Any], *, return_path: bool = False, delete: bool = False
    ) -> Any | str | tuple[Any, list[str | int] | None]:
        """Extract the value whose key contains key_substr. Uses cached path if
        available; otherwise searches and caches.

        :param obj: dict/list parsed from JSON
        :param return_path: if True, return (value, path)
        :param delete: if True, delete the found field from obj after
            extraction
        :return: value or (value, path) or (None / (None, None)) if not
            found
        """
        path = self._cached_path

        # 1. Try cached path first
        if path is not None:
            try:
                value = self._get_by_path(obj, path)
                if delete:
                    self._del_by_path(obj, path)
                return (value, path) if return_path else value
            except (KeyError, IndexError, TypeError):
                # structure changed; invalidate cache & fall back
                path = None
                self._cached_path = None

        # 2. Full search
        path = self._find_path(obj)
        if path is None:
            return (None, None) if return_path else None

        # 3. Cache and return
        self._cached_path = path
        value = self._get_by_path(obj, path)
        if delete:
            self._del_by_path(obj, path)
        return (value, path) if return_path else value
