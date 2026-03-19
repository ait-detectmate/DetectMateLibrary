from detectmatelibrary.detectors.new_value_detector import NewValueDetector, NewValueDetectorConfig
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From

import pytest
import json

AUDIT_LOG = "tests/test_folder/audit.log"
AUDIT_TEMPLATES = "tests/test_folder/audit_templates.txt"
ANOMALY_LABELS = "tests/test_folder/audit_anomaly_labels.log"
LOG_FORMAT = "type=<Type> msg=audit(<Time>): <Content>"
TRAIN_UNTIL = 1800


def load_expected_anomaly_ids() -> set[str]:
    """Load labeled anomaly logIDs from the labels file (line numbers are
    1-indexed)."""
    with open(ANOMALY_LABELS) as f:
        return {str(json.loads(line)["line"] - 1) for line in f if line.strip()}


parser_config = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": LOG_FORMAT,
            "params": {"path_templates": AUDIT_TEMPLATES},
        }
    }
}


class TestConfigurationEngineManual:
    """Mirrors the manual flow in 05_configuration_engine/detect.py."""
    @pytest.mark.skip(reason="no way of currently testing this")
    def test_configure_train_detect(self) -> None:
        parser = MatcherParser(config=parser_config)
        detector = NewValueDetector()

        logs = [log for log in From.log(parser, AUDIT_LOG, do_process=True) if log is not None]

        for log in logs[:TRAIN_UNTIL]:
            detector.configure(log)
        detector.set_configuration()

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        anomalies = []
        for log in logs[TRAIN_UNTIL:]:
            if (output := detector.process(log)) is not None:
                anomalies.append(output)

        detected_ids = {lid for out in anomalies for lid in out["logIDs"]}
        assert detected_ids.issubset(load_expected_anomaly_ids())
        assert len(detected_ids) > 0


class TestConfigurationEngineAutomatic:
    """Tests the automated configure phase via process()."""

    @pytest.mark.skip(reason="no way of currently testing this")
    def test_process_configure_train_detect(self) -> None:
        parser = MatcherParser(config=parser_config)
        config = NewValueDetectorConfig(data_use_configure=TRAIN_UNTIL)
        detector = NewValueDetector(config=config)

        logs = [log for log in From.log(parser, AUDIT_LOG, do_process=True) if log is not None]

        # Auto-configure: process() returns None during configure phase and calls
        # set_configuration() automatically on the first log after configure ends.
        for log in logs:
            detector.process(log)

        assert detector.fitlogic.data_used_configure == TRAIN_UNTIL
        assert detector.fitlogic._configuration_done is True

        # Train on same logs used for configuration (mirrors detect.py)
        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        # Detect via process()
        anomalies = []
        for log in logs[TRAIN_UNTIL:]:
            if (output := detector.process(log)) is not None:
                anomalies.append(output)

        detected_ids = {lid for out in anomalies for lid in out["logIDs"]}
        assert detected_ids.issubset(load_expected_anomaly_ids())
        assert len(detected_ids) > 0
