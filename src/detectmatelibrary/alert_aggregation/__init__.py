# mypy: ignore-errors

from .basic_concat import BasicConcatAggregation, BasicConcatAggregationConfig
from .logid_count import LogIDCountAggegation, LogIDCountAggegationConfig
from .time_delta import TimeDeltaAggregation, TimeDeltaAggregationConfig

__all__ = [
    "BasicConcatAggregation",
    "BasicConcatAggregationConfig",
    "TimeDeltaAggregation",
    "TimeDeltaAggregationConfig",
    "LogIDCountAggegation",
    "LogIDCountAggegationConfig",
]


def __getattr__(name):
    """Load AlertBERT only when one of its exports is requested."""
    if name in {"AlertBERTAggregation", "AlertBERTAggregationConfig"}:
        from .alertbert import AlertBERTAggregation, AlertBERTAggregationConfig

        # Cache both exports for subsequent attribute access.
        globals().update(
            AlertBERTAggregation=AlertBERTAggregation,
            AlertBERTAggregationConfig=AlertBERTAggregationConfig,
        )
        return globals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
