"""Tests for detectmatelibrary.base_detectors.count_vector_detector."""
from detectmatelibrary.base_detectors import CountVectorDetectorConfig
from detectmatelibrary.detectors.ecvc_detector import ECVCDetector, ECVCDetectorConfig


def test_config_base_defaults():
    c = CountVectorDetectorConfig()
    assert c.window_size == 10 and c.session_variable is None


def test_sync_from_state_runs_before_windows_exist():
    # TrackerDetector.__init__ calls _sync_from_state before CountVectorDetector sets its windows.
    detector = ECVCDetector(config=ECVCDetectorConfig(session_variable="blk"))
    assert detector.window == ()
