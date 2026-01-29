from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import polars as pl

from ..base import EventDataStructure


# -------- Polars backends --------
@dataclass
class ChunkedEventDataFrame(EventDataStructure):
    """
    Streaming-friendly Polars DataFrame backend:
    - Ingest appends chunks (cheap)
    - Retention by max_rows is handled internally
    - DataFrame is materialized on demand
    """
    max_rows: Optional[int] = 10_000_000
    compact_every: int = 1000

    chunks: list[pl.DataFrame] = field(default_factory=list)
    _rows: int = 0

    def add_data(self, data: pl.DataFrame) -> None:
        if data.height == 0:
            return
        self.chunks.append(data)
        self._rows += data.height

        if self.max_rows is not None:
            self._evict_oldest()

        if len(self.chunks) > self.compact_every:
            self._compact()

    def _evict_oldest(self) -> None:
        if self.max_rows is not None:
            overflow = self._rows - self.max_rows
        if overflow <= 0:
            return

        # drop whole chunks
        while self.chunks and overflow >= self.chunks[0].height:
            oldest = self.chunks.pop(0)
            overflow -= oldest.height
            self._rows -= oldest.height

        # trim remaining overflow from the oldest chunk
        if overflow > 0 and self.chunks:
            oldest = self.chunks[0]
            keep = oldest.height - overflow
            self.chunks[0] = oldest.tail(keep)
            self._rows -= overflow

    def _compact(self) -> None:
        if not self.chunks:
            return
        df = pl.concat(self.chunks, how="vertical", rechunk=False)
        self.chunks = [df]
        self._rows = df.height

    def get_data(self) -> pl.DataFrame:
        if not self.chunks:
            return pl.DataFrame()
        if len(self.chunks) == 1:
            return self.chunks[0]
        return pl.concat(self.chunks, how="vertical", rechunk=False)

    def get_variables(self) -> Any:
        if not self.chunks:
            return []
        return self.chunks[0].columns

    def to_data(self, raw_data: Dict[str, List[Any]]) -> pl.DataFrame:
        return pl.DataFrame(raw_data)

    def __repr__(self) -> str:
        return (
            f"ChunkedEventDataFrame(df=..., rows={self._rows}, chunks={len(self.chunks)}, "
            f"variables={self.get_variables()})"
        )
