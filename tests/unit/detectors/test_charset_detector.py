"""Tests for CharsetDetector class.

This module tests the CharsetDetector implementation including:
- Initialization and configuration
- Training functionality to learn known characters
- Detection logic for new/unknown characters
- Event-specific configuration handling
- Input/output schema validation
"""

from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as sc
from tests.support.audit import TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

import pytest

# Set time test mode for consistent timestamps
pytestmark = pytest.mark.usefixtures("frozen_timestamps")


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "charset_detector",
            "auto_config": False,
            "params": {},
            "events": {
                1: {
                    "instance1": {
                        "params": {},
                        "variables": [{
                            "pos": 0, "name": "sad", "params": {}
                        }]
                    }
                }
            }
        },
        "MultipleDetector": {
            "method_type": "charset_detector",
            "auto_config": False,
            "params": {},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{
                            "pos": 1, "name": "test", "params": {}
                        }],
                        "header_variables": [{
                            "pos": "level", "params": {}
                        }]
                    }
                }
            }
        }
    }
}


def _event_1_record(log_id: str, value: str) -> sc.ParserSchema:
    return sc.ParserSchema({
        "parserType": "test", "eventID": 1, "template": "test template", "variables": ["adsasd", value],
        "logID": log_id, "parsedLogID": log_id, "parserID": "test_parser", "log": "test log message",
        "headerVariables": {"level": "INFO"},
    })


class TestCharsetDetectorStores:
    """What the detector keeps in its stores."""

    def test_persistency_uses_custom_add_value(self):
        """Main persistency must accumulate characters; auto_conf must not."""
        detector = CharsetDetector()
        # Ingest a sample so a SingleStabilityTracker is materialized
        detector.persistency.ingest_event(
            event_id=1,
            event_template="t",
            named_variables={"v": "hello"},
        )
        single = detector.persistency.get_event_data(1)["v"]
        assert single.unique_set == {"h", "e", "l", "o"}


class TestCharsetDetectorTraining:
    """Test CharsetDetector training functionality."""

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        detector = CharsetDetector(config=config, name="MultipleDetector")
        # Train with multiple values (only event 1 should be tracked per config)
        for event in range(3):
            for level in ["INFO", "WARNING", "ERROR"]:
                parser_data = sc.ParserSchema({
                    "parserType": "test",
                    "eventID": event,
                    "template": "test template",
                    "variables": ["0", "assa"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "headerVariables": {"level": level}
                })
                detector.train(parser_data)

        # Only event 1 should be tracked (based on events config)
        assert len(detector.persistency) == 1
        event_data = detector.persistency.get_event_data(1)
        assert event_data is not None
        # With expand_value=True, unique_set contains individual characters
        assert set("INFO") <= event_data["level"].unique_set
        assert set("WARNING") <= event_data["level"].unique_set
        assert set("ERROR") <= event_data["level"].unique_set
        assert set("assa") <= event_data["test"].unique_set


class TestCharsetDetectorDetection:
    """Test CharsetDetector detection functionality."""

    def test_detect_ignores_unconfigured_event(self):
        detector = CharsetDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # EventID 12 is not in the config, so nothing is checked
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 12,
            "template": "test template",
            "variables": ["adsasddddddaaa"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "CRITICAL"}
        })
        output = sc.DetectorSchema()

        result = detector.detect(test_data, output)

        assert not result
        assert output.score == 0.0

    def test_detect_known_value_no_alert(self):
        """Event 1 checks variable 1 and the header `level` (module config)."""
        detector = CharsetDetector(config=config, name="MultipleDetector")
        detector.train(_event_1_record("1", "asdasd"))

        assert detector.detect(_event_1_record("2", "asdasd"), sc.DetectorSchema()) is False
        assert detector.detect(_event_1_record("3", "qwqwqw"), sc.DetectorSchema()) is True

    def test_detect_known_value_alert(self):
        detector = CharsetDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["asas", "adsd"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "CRITICAL"}
        })
        output = sc.DetectorSchema()

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0

    def test_detect_unknown_chars_reported_per_variable(self):
        """Train on a known alphabet; detect a value with unknown chars and
        confirm the alert string lists the unknown chars sorted."""
        cfg = {
            "detectors": {
                "Single": {
                    "method_type": "charset_detector",
                    "auto_config": False,
                    "params": {},
                    "events": {
                        1: {
                            "test": {
                                "params": {},
                                "variables": [{"pos": 0, "name": "v", "params": {}}],
                            }
                        }
                    },
                }
            }
        }
        detector = CharsetDetector(config=cfg, name="Single")

        train = sc.ParserSchema({
            "parserType": "test", "eventID": 1, "template": "t",
            "variables": ["abc"], "logID": "1", "parsedLogID": "1",
            "parserID": "p", "log": "l", "headerVariables": {},
        })
        detector.train(train)

        # All known chars
        ok = sc.ParserSchema({
            "parserType": "test", "eventID": 1, "template": "t",
            "variables": ["cba"], "logID": "2", "parsedLogID": "2",
            "parserID": "p", "log": "l", "headerVariables": {},
        })
        out = sc.DetectorSchema()
        assert not detector.detect(ok, out)
        assert out.score == 0.0

        # Unknown chars 'x' and 'y'
        bad = sc.ParserSchema({
            "parserType": "test", "eventID": 1, "template": "t",
            "variables": ["axy"], "logID": "3", "parsedLogID": "3",
            "parserID": "p", "log": "l", "headerVariables": {},
        })
        out = sc.DetectorSchema()
        assert detector.detect(bad, out)
        assert out.score == 1.0
        assert any("'x'" in msg and "'y'" in msg for msg in out["alertDetails"].values())


_PARSER_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>): <Content>",
            "time_format": None,
            "params": {
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True,
                "path_templates": AUDIT_TEMPLATES,
            },
        }
    }
}


class TestCharsetDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.slow
    def test_audit_log_anomalies_to_binary(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = CharsetDetector(config=CharsetDetectorConfig(allow_fed=True))
        detector2 = CharsetDetector(config=CharsetDetectorConfig(allow_fed=True))

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.configure(log)
            detector2.configure(log)
        detector.set_configuration()
        detector2.set_configuration()

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        detector2 = detector2.from_binary(detector.to_binary())
        assert detector2.persistency == detector.persistency

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = sc.DetectorSchema()
            if detector2.detect(log, output_=output):
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}

    @pytest.mark.slow
    def test_audit_log_anomalie_fed(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector1 = CharsetDetector(config=CharsetDetectorConfig(allow_fed=True))
        detector2 = CharsetDetector(config=CharsetDetectorConfig(allow_fed=True))

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs[:TRAIN_UNTIL]:
            detector1.configure(log)
            detector2.configure(log)

        detector1.set_configuration()
        detector2.set_configuration()

        for i, log in enumerate(logs[:TRAIN_UNTIL]):
            if i < 10:
                detector1.train(log)
            else:
                detector2.train(log)

        assert detector2.persistency != detector1.persistency

        (detector1 + detector2).aggregate()
        assert detector2.persistency == detector1.persistency
        assert len(detector2.persistency) != 0

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            if detector1.process(log) is not None:
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}
