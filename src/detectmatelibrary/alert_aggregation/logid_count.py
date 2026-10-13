from detectmatelibrary.common.alert_aggregator import (
    CoreAlertAggregatorConfig, CoreAlertAggregator
)

from detectmatelibrary.schemas import DetectorSchema, AggregateSchema
from detectmatelibrary.utils.data_buffer import BufferMode

from typing import Any, Optional
from functools import lru_cache
from pydantic import Field
import polars as pl


class Counter:
    def __init__(self, max_count: int, overall_size: int) -> None:
        self.max_count = max_count
        
        self._df = pl.DataFrame()
        self._df = self._df.insert_column(0, pl.repeat("", n=overall_size).alias("LogID"))
        self._df = self._df.insert_column(1, pl.zeros(overall_size, dtype=pl.UInt8).alias("Count"))
        self._df = self._df.insert_column(2, pl.zeros(overall_size, dtype=pl.Boolean).alias("WasAlert"))
        self._df = self._df.with_row_index(name="Index")

        self._cached_search = lru_cache(maxsize=overall_size)(self.__get_idx)

        self.idx = 0

    def __is_new_alert(self, idx: int) -> bool:
        if not self._df[idx, "WasAlert"] and self._df[idx, "Count"] >= self.max_count:
            self._df[idx, "WasAlert"] = True
            return True
        return False

    def __get_idx(self, logId: str) -> int:
        indices = self._df.filter(pl.col("LogID") == logId).select("Index").to_series()

        if indices.shape[0] == 0:
            new_row = pl.DataFrame(
                data=[[self.idx, logId, 0, False]], schema=self._df.schema, orient="row"
            )
            self._df = self._df.update(new_row, on="Index")
            idx = self.idx
            self.idx = self.idx + 1 if self.idx < self._df.shape[0] - 1 else 0
        else:
            idx = indices[0]

        return idx

    def add_and_check(self, logId: str) -> bool:
        idx = self._cached_search(logId)
        self._df[idx, "Count"] += 1
        return self.__is_new_alert(idx)


class LogIDCountAggegationConfig(CoreAlertAggregatorConfig):
    method_type: str = Field(
        default="logid_count_aggregator", description="Indicates what type of method it is."
    )
    max_count: int = Field(default=4, description="Max count of alerts in a specific logID.")
    max_memory: int = Field(
        default=5000, description="Max number of logIDs store in the count memory."
    )


class LogIDCountAggegation(CoreAlertAggregator):
    def __init__(
        self,
        name: str = "LogIDCountAggregator",
        config: Optional[LogIDCountAggegationConfig | dict[str, Any]] = LogIDCountAggegationConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = LogIDCountAggegationConfig.from_dict(config, name)

        super().__init__(name=name, config=config, buffer_mode=BufferMode.NO_BUF, buffer_size=None)
        self.config: LogIDCountAggegationConfig

        self.counter = Counter(
            max_count=self.config.max_count, overall_size=self.config.max_memory
        )

    def aggregate_alerts(
        self, input_: DetectorSchema, output_: AggregateSchema  # type: ignore
    ) -> bool:

        alert_logs = []
        for logID in input_["logIDs"]:
            if self.counter.add_and_check(logID):
                alert_logs.append(logID)

        if (aggreated_alerts := len(alert_logs) > 0):
            output_["description"] = (
                "LogID count how many times a log was count as alert."
                f"Logs that pass the limit count: {", ".join(alert_logs)}"
            )

        return aggreated_alerts
