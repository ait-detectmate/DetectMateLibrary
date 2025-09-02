from collections import deque
from typing import Any, Callable, Optional, Literal
import copy


class DataBuffer:
    """
    High-performance buffer for managing incoming data in different modes:

    Modes:
    1. Batch buffer: Processes data_points in fixed-size batches.
    2. Bulk buffer: Stores all data_points, processes them on flush.
    3. Window buffer: Processes data_points in a sliding window of fixed size.
    """

    def __init__(
        self,
        mode: Optional[Literal["no_buf", "batch", "window"]],
        process_function: Callable = lambda x: x,
        size: Optional[int] = None,
    ):
        if mode not in {"no_buf", "batch", "window"}:
            raise ValueError("mode must be 'no_buf', 'batch' or 'window'")
        self.mode = mode
        self.size = size or 0
        self.process_function = process_function
        self.add = lambda x: None
        self.buffer: deque = deque()
        if mode == "no_buf":
            if size:
                raise ValueError("'size' should not be set for mode 'no_buf'.")
            self.add = self.process_function
        elif mode == "batch":
            if not size or size <= 1:
                raise ValueError("'size' must be > 1 for mode 'batch'.")
            self.buffer = deque()
            self.add = self._add_batch
        elif mode == "window":
            if not size:
                raise ValueError(
                    "'size' must be a positive integer for mode 'window'."
                )
            # automatic discarding of old items with deque
            self.buffer = deque(maxlen=size)
            self.add = self._add_window

    def _add_batch(self, data_point: Any):
        self.buffer.append(data_point)
        if len(self.buffer) >= self.size:
            return self._process_and_clear(self.buffer)

    def _add_window(self, data_point: Any):
        self.buffer.append(data_point)
        if len(self.buffer) == self.size:
            return self.process_function(self.buffer)

    def _process_and_clear(self, buf: deque, clear: bool = True):
        """Process and optionally clear the buffer."""
        result = copy.copy(self.process_function(buf))
        if clear:
            buf.clear()
        return result

    def flush(self):
        """Process remaining data_points."""
        if self.buffer:
            clear = self.mode != "window"
            return self._process_and_clear(self.buffer, clear=clear)
