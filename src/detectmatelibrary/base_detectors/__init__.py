"""Detector base classes built on ``common``.

``TrackerDetector`` is the only boundary to ``utils.persistency``: detectors
that keep their model in EventPersistency stores subclass it (or
``VariableDetector``) and import the tracker types from here.
"""
from detectmatelibrary.utils.persistency.data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
    SingleStabilityTracker,
)

from ._persist import PersistConfig
from .deeplearning_detector import DeepLearningDetector, DeepLearningDetectorConfig
from ._stability import StabilityAutoConfigParams
from .tracker_detector import TrackerDetector, TrackerDetectorConfig
from .variable_detector import VariableAutoConfigParams, VariableDetector, VariableDetectorConfig

__all__ = [
    "DeepLearningDetector",
    "DeepLearningDetectorConfig",
    "EventStabilityTracker",
    "PersistConfig",
    "SingleStabilityTracker",
    "StabilityAutoConfigParams",
    "TrackerDetector",
    "TrackerDetectorConfig",
    "VariableAutoConfigParams",
    "VariableDetector",
    "VariableDetectorConfig",
]
