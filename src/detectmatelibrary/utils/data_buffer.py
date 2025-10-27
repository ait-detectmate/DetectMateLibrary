from typing import Any, Callable, Optional, Literal
from collections import deque


class ArgsBuffer:
    """Arguments for DataBuffer class."""
    def __init__(
        self,
        mode: Optional[Literal["no_buf", "batch", "window"]],
        process_function: Callable = lambda x: x,
        size: Optional[int] = None,
    ) -> None:

        self.mode = mode
        self.size = size
        self.process_function = process_function
        self.add = lambda x: None

        self.is_correct_format()

    def is_correct_format(self) -> None | ValueError:
        if self.mode not in {"no_buf", "batch", "window"}:
            raise ValueError("'mode' must be 'no_buf', 'batch' or 'window'")

        if self.mode == "no_buf":
            if self.size:
                raise ValueError("'size' should not be set for mode 'no_buf'.")
        elif self.mode == "batch":
            if not self.size or self.size <= 1:
                raise ValueError("'size' must be > 1 for mode 'batch'.")
        elif self.mode == "window":
            if not self.size:
                raise ValueError(
                    "'size' must be a positive integer for mode 'window'."
                )
        return None


class DataBuffer:
    """
    Buffer for managing incoming data in different modes:

    Modes:
    1. Batch buffer: Processes data_points in fixed-size batches.
    2. Bulk buffer: Stores all data_points, processes them on flush.
    3. Window buffer: Processes data_points in a sliding window of fixed size.
    """

    def __init__(self, args: ArgsBuffer = ArgsBuffer("no_buf")) -> None:
        self.mode = args.mode
        self.size = args.size
        self.process_function = args.process_function
        self.add = args.add
        self.buffer: deque = deque() if self.mode != "window" else deque(maxlen=self.size)

        if self.mode == "window":
            self.add = self._add_window
        elif self.mode == "batch":
            self.add = self._add_batch
        else:
            self.add = self.process_function

    def _is_full(self) -> bool:
        """Determine if the buffer is full."""
        if self.size is not None:
            return len(self.buffer) == self.size
        return False

    def _add_batch(self, data_point: Any) -> Any:
        """Add data_point to the batch buffer and process if full."""
        self.buffer.append(data_point)
        if self._is_full():
            return self._process_and_clear(self.buffer)

    def _add_window(self, data_point: Any) -> Any:
        """Add data_point to the window buffer and process if full."""
        self.buffer.append(data_point)
        if self._is_full():
            return self.process_function(list(self.buffer))

    def _process_and_clear(self, buf: deque, clear: bool = True) -> Any:
        """Process and optionally clear the buffer."""
        buf_copy = list(buf)
        result = self.process_function(buf_copy)
        if clear:
            buf.clear()
        return result

    def flush(self) -> Any:
        """Process remaining data_points."""
        if self.buffer:
            clear = self.mode != "window"
            return self._process_and_clear(self.buffer, clear=clear)
