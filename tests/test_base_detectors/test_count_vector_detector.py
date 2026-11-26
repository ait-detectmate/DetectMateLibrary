from detectmatelibrary.bases.base_detectors import CountVectorDetector, CountVectorDetectorConfig
from detectmatelibrary.bases.base_detectors import count_vector_detector
from detectmatelibrary.detectors import ecvc_detector
from detectmatelibrary.detectors.ecvc_detector import ECVCDetector, ECVCDetectorConfig


def test_ecvc_is_a_count_vector_detector():
    assert issubclass(ECVCDetector, CountVectorDetector)
    assert issubclass(ECVCDetectorConfig, CountVectorDetectorConfig)


def test_session_windows_still_importable_from_ecvc():
    assert ecvc_detector.SessionWindows is count_vector_detector.SessionWindows


def test_config_base_defaults():
    c = CountVectorDetectorConfig()
    assert c.window_size == 10 and c.session_variable is None


def test_ecvc_config_surface_unchanged():
    fields = ECVCDetectorConfig.model_fields
    names = ("method_type", "window_size", "validation_per", "seed", "threshold_method", "session_variable")
    assert {k: fields[k].default for k in names} == {
        "method_type": "ecvc_detector", "window_size": 10, "validation_per": 0.2, "seed": 0,
        "threshold_method": "mean", "session_variable": None}


def test_sync_from_state_runs_before_windows_exist():
    # TrackerDetector.__init__ calls _sync_from_state before CountVectorDetector sets its windows.
    detector = ECVCDetector(config=ECVCDetectorConfig(session_variable="blk"))
    assert detector.window == ()
