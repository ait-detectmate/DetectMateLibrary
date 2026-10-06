"""Configure-phase records kept for training, spilled to disk when there are
many.

With ``use_config_data_as_training`` a component keeps every configure record
and replays it into ``train()`` once configuration ends. Up to ``max_records``
records stay in memory; each time that many have piled up they are written as
one Parquet part file to a private temporary directory, and replay reads the
parts back in order. The directory is removed after replay, when the buffer is
garbage collected, or at interpreter exit.

In WINDOW mode every record is a window that moves one log on from the window
before it, so only the logs are written, each once, and replay rebuilds the
windows from them.
"""
import tempfile
from collections import deque
from pathlib import Path
from typing import Iterator, cast

import pyarrow as pa
import pyarrow.parquet as pq

from detectmatelibrary.schemas import BaseSchema
from detectmatelibrary.tools.logging import logger

Record = BaseSchema | list[BaseSchema]


def _serialize(record: Record) -> bytes | list[bytes]:
    if isinstance(record, list):  # a BATCH-mode batch
        return [r.serialize() for r in record]
    return record.serialize()


class TrainBuffer:
    """Records in insertion order: in memory up to ``max_records``, then in
    Parquet part files under ``spill_dir``.

    Iterating replays every record once, in order, and empties the
    buffer.
    """

    def __init__(
        self,
        schema_class: type[BaseSchema],
        max_records: int = 100_000,
        spill_dir: str | None = None,
        window: int | None = None,
        name: str = "component",
    ) -> None:
        self.schema_class = schema_class  # decodes the spilled records
        self.max_records = max_records
        self.spill_dir = spill_dir  # None: the system temp directory
        self.window = window  # the window size, when records are sliding windows
        self.name = name
        self._memory: list[Record] = []
        self._parts: list[Path] = []
        self._tmp: tempfile.TemporaryDirectory[str] | None = None

    def add(self, record: Record) -> None:
        self._memory.append(record)
        if len(self._memory) >= self.max_records:
            self._spill()

    def __iter__(self) -> Iterator[Record]:
        logs: deque[BaseSchema] = deque(maxlen=self.window)
        for path in self._parts:
            for blob in pq.read_table(path).column("record").to_pylist():
                if self.window is not None:
                    logs.append(self._decode(blob))
                    if len(logs) == self.window:
                        yield list(logs)
                elif isinstance(blob, list):
                    yield [self._decode(b) for b in blob]
                else:
                    yield self._decode(blob)
        yield from self._memory
        self.clear()

    def clear(self) -> None:
        """Drop every record and remove the spill directory."""
        self._memory = []
        self._parts = []
        if self._tmp is not None:
            try:
                self._tmp.cleanup()
            except OSError as e:
                logger.warning(f"{self.name}: could not remove {self._tmp.name} ({e}); delete it by hand.")
            self._tmp = None

    def _spill(self) -> None:
        """Write the in-memory records as the next part file."""
        if self._tmp is None:
            if self.spill_dir is not None:
                Path(self.spill_dir).mkdir(parents=True, exist_ok=True)
            self._tmp = tempfile.TemporaryDirectory(prefix="detectmate-train-", dir=self.spill_dir)
            logger.warning(
                f"{self.name}: more than {self.max_records} configure records are kept to be read "
                f"again later, so they now go to disk in {self._tmp.name} until then. To avoid this, "
                "lower data_use_configure; to change it, set train_buffer_max_records or train_buffer_dir."
            )
        path = Path(self._tmp.name) / f"part-{len(self._parts):05d}.parquet"
        pq.write_table(pa.table({"record": self._encode()}), path, compression="zstd")
        self._parts.append(path)  # only once the part is complete
        self._memory = []

    def _encode(self) -> pa.Array:
        if self.window is not None:
            windows = cast(list[list[BaseSchema]], self._memory)
            # The first part holds the whole first window, then each window adds its last log.
            logs = (windows[0][:-1] if not self._parts else []) + [w[-1] for w in windows]
            return pa.array([log.serialize() for log in logs], type=pa.large_binary())
        is_batch = isinstance(self._memory[0], list)
        return pa.array(
            [_serialize(r) for r in self._memory],
            type=pa.list_(pa.large_binary()) if is_batch else pa.large_binary(),
        )

    def _decode(self, blob: bytes) -> BaseSchema:
        record = self.schema_class()
        record.deserialize(blob)
        return record
