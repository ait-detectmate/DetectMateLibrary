from typing import Any

from .random_detector import RandomDetector, RandomDetectorConfig
from .rule_detector import RuleDetector, RuleDetectorConfig
from .new_event_detector import NewEventDetector, NewEventDetectorConfig
from .new_value_detector import NewValueDetector, NewValueDetectorConfig
from .new_value_combo_detector import NewValueComboDetector, NewValueComboDetectorConfig
from .value_range_detector import ValueRangeDetector, ValueRangeDetectorConfig
from .charset_detector import CharsetDetector, CharsetDetectorConfig
from .event_sequence_detector import EventSequenceDetector, EventSequenceDetectorConfig
from .bigram_frequency_detector import BigramFrequencyDetector, BigramFrequencyDetectorConfig
from .scvs_detector import SCVSDetector, SCVSDetectorConfig
from .ecvc_detector import ECVCDetector, ECVCDetectorConfig

# The deep learning detectors load JAX/Flax, so they are imported on first
# access rather than with the package.
_LAZY = {
    "DeeplogDetector": ".deeplog_detector",
    "DeeplogDetectorConfig": ".deeplog_detector",
    "LogBertDetector": ".logbert_detector",
    "LogBertDetectorConfig": ".logbert_detector",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        return getattr(import_module(_LAZY[name], __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "RandomDetector",
    "RandomDetectorConfig",
    "RuleDetector",
    "RuleDetectorConfig",
    "NewEventDetector",
    "NewEventDetectorConfig",
    "NewValueDetector",
    "NewValueDetectorConfig",
    "NewValueComboDetector",
    "NewValueComboDetectorConfig",
    "ValueRangeDetector",
    "ValueRangeDetectorConfig",
    "CharsetDetector",
    "CharsetDetectorConfig",
    "EventSequenceDetector",
    "EventSequenceDetectorConfig",
    "BigramFrequencyDetector",
    "BigramFrequencyDetectorConfig",
    "SCVSDetector",
    "SCVSDetectorConfig",
    "ECVCDetector",
    "ECVCDetectorConfig",
    "DeeplogDetector",
    "DeeplogDetectorConfig",
    "LogBertDetector",
    "LogBertDetectorConfig",
]
