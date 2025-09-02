from collections import deque
from typing import Any, Callable, Iterable, Optional, Literal
import copy

class DataBuffer:
    """
    High-performance buffer for managing incoming data in different modes:
    
    Modes:
    1. Batch buffer: Processes data_points in fixed-size batches.
    2. Bulk buffer: Stores all data_points, processes them on flush.
    3. Window buffer: Processes data_points in a sliding window of fixed size.
    """

    # __slots__ = ("mode", "size", "process_function", "function_config", "buffer", "add")

    def __init__(
        self, 
        mode: Optional[Literal["no_buf", "batch", "window"]], 
        process_function: Callable[[Iterable[Any]], None],
        size: Optional[int] = None, 
    ):
        if mode not in {"no_buf", "batch", "window"}:
            raise ValueError("mode must be 'no_buf', 'batch' or 'window'")
        self.mode = mode
        self.size = size
        self.process_function = process_function
        self.add = None
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
                raise ValueError("'size' must be a positive integer for mode 'window'.")
            self.buffer = deque(maxlen=size)  # automatic discarding of old items
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
        result = copy.copy(self.process_function(buf))  # process deque directly, no list() conversion
        if clear:
            buf.clear()
        return result

    def flush(self):
        """Process any remaining data_points (mainly for bulk or leftover batch)."""
        if self.buffer:
            return self._process_and_clear(self.buffer, clear=(self.mode != "window"))