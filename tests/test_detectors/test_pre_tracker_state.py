"""State saved before the TrackerDetector refactor still restores.

The files in tests/test_data/pre_tracker_state/ were written by
``export_state()`` on the code before ``subcommon/`` existed (``development``
at fa3f4a1), by ``write_fixtures()`` below. Never regenerate them with newer
code: their whole point is to be old. Users upgrade with ``persist:``
directories written by that code, and the refactor must not change the
format.
"""
from pathlib import Path

import numpy as np

from detectmatelibrary import schemas
from detectmatelibrary.detectors.charset_detector import CharsetDetector
from detectmatelibrary.detectors.ecvc_detector import ECVCDetector, ECVCDetectorConfig
from detectmatelibrary.detectors.event_sequence_detector import (
    EventSequenceDetector,
    EventSequenceDetectorConfig,
)

FIXTURES = Path(__file__).parent.parent / "test_data" / "pre_tracker_state"

_CHARSET_CONFIG = {
    "detectors": {
        "CharsetDetector": {
            "method_type": "charset_detector",
            "auto_config": False,
            "events": {1: {"login": {"variables": [{"pos": 0, "name": "user"}]}}},
        }
    }
}
_SEQUENCE = [1, 2, 3, 1, 2, 3]
_ECVC_WINDOWS = [[1, 2, 3], [1, 1, 2], [2, 3, 3], [1, 2, 3]]


def _event(event_id: int, variables: list[str] | None = None) -> schemas.ParserSchema:
    return schemas.ParserSchema({
        "EventID": event_id, "template": "login <*>", "variables": variables or [], "logID": "1",
    })


def _charset() -> CharsetDetector:
    return CharsetDetector(config=_CHARSET_CONFIG)


def _sequence(fixed_window_size: int = 3) -> EventSequenceDetector:
    return EventSequenceDetector(
        config=EventSequenceDetectorConfig(auto_config=False, fixed_window_size=fixed_window_size)
    )


def _ecvc() -> ECVCDetector:
    return ECVCDetector(config=ECVCDetectorConfig(window_size=3))


def _trained() -> dict[str, CharsetDetector | EventSequenceDetector | ECVCDetector]:
    charset = _charset()
    for user in ["alice", "bob"]:
        charset.train(_event(1, [user]))
    sequence = _sequence()
    for event_id in _SEQUENCE:
        sequence.train(_event(event_id))
    ecvc = _ecvc()
    for window in _ECVC_WINDOWS:
        ecvc.train([_event(event_id) for event_id in window])
    ecvc.post_train()
    return {"charset": charset, "event_sequence": sequence, "ecvc": ecvc}


def write_fixtures() -> None:
    """Write the fixtures.

    Run only on the pre-refactor code (see module docstring).
    """
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name, detector in _trained().items():
        (FIXTURES / f"{name}.zip").write_bytes(detector.export_state())


def _restore[D: CharsetDetector | EventSequenceDetector | ECVCDetector](detector: D, name: str) -> D:
    detector.import_state((FIXTURES / f"{name}.zip").read_bytes())
    return detector


def _alerts(detector: CharsetDetector, user: str) -> bool:
    return detector.detect(_event(1, [user]), schemas.DetectorSchema())


class TestPreTrackerState:
    def test_charset_rebuilds_its_trackers_and_detects_the_same(self) -> None:
        restored = _restore(_charset(), "charset")
        assert restored.persistency.get_events_seen() == {1}
        assert not _alerts(restored, "bob")
        assert _alerts(restored, "zed")

    def test_event_sequence_adopts_the_saved_length(self) -> None:
        restored = _restore(_sequence(fixed_window_size=4), "event_sequence")
        assert restored.config.fixed_window_size == 3
        assert restored.get_known_sequences() == {(1, 2, 3), (2, 3, 1), (3, 1, 2)}

    def test_ecvc_rebuilds_the_same_count_vectors(self) -> None:
        restored = _restore(_ecvc(), "ecvc")
        fresh = _trained()["ecvc"]
        assert restored.persistency.get_events_seen() == fresh.persistency.get_events_seen()
        assert restored.count_vecs is not None and fresh.count_vecs is not None
        assert np.array_equal(restored.count_vecs, fresh.count_vecs)
        assert restored.threshold == fresh.threshold
