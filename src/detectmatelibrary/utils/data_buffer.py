from typing import Any, Callable, Optional
from collections import deque
from enum import Enum


class BufferMode(Enum):
    NO_BUF = "no_buf"
    BATCH = "batch"
    WINDOW = "window"

    def describe(self) -> str:
        descriptions = {
            "no_buf": "Return one value at the time.",
            "batch": "Return values by batches.",
            "window": "Return values by time windows."
        }
        return descriptions[self.value]


class ArgsBuffer:
    """Arguments for DataBuffer class."""
    def __init__(
        self,
        mode: BufferMode = BufferMode.NO_BUF,
        process_function: Callable[[Any], Any] = lambda x: x,
        size: Optional[int] = None,
    ) -> None:

        self.mode = mode
        self.size = size
        self.process_function = process_function
        self.add = lambda x: None

        self.is_correct_format()

    def is_correct_format(self) -> None | ValueError:
        if not isinstance(self.mode, BufferMode):
            raise ValueError("'mode' must be 'no_buf', 'batch' or 'window'")

        if self.mode == BufferMode.NO_BUF:
            if self.size:
                raise ValueError("'size' should not be set for mode 'no_buf'.")
        elif self.mode == BufferMode.BATCH:
            if not self.size or self.size <= 1:
                raise ValueError("'size' must be > 1 for mode 'batch'.")
        elif self.mode == BufferMode.WINDOW:
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

    def __init__(self, args: ArgsBuffer = ArgsBuffer(BufferMode.NO_BUF)) -> None:
        self.mode = args.mode
        self.size = args.size
        self.process_function = args.process_function
        self.add = args.add
        self.buffer: deque[Any] = deque() if self.mode != BufferMode.WINDOW else deque(maxlen=self.size)

        if self.mode == BufferMode.WINDOW:
            self.add = self._add_window
        elif self.mode == BufferMode.BATCH:
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

    def _process_and_clear(self, buf: deque[Any], clear: bool = True) -> Any:
        """Process and optionally clear the buffer."""
        buf_copy = list(buf)
        result = self.process_function(buf_copy)
        if clear:
            buf.clear()
        return result

    def get_buffer(self) -> deque[Any]:
        """Get the current buffer."""
        return self.buffer

    def flush(self) -> Any:
        """Process remaining data_points."""
        if self.buffer:
            clear = self.mode != BufferMode.WINDOW
            return self._process_and_clear(self.buffer, clear=clear)

    def __repr__(self) -> str:
        return f"DataBuffer(mode={self.mode}, capacity={self.size}, current_length={len(self.buffer)})"
