"""Tests for CharsetDetector class.

This module tests the CharsetDetector implementation including:
- Initialization and configuration
- Training functionality to learn known characters
- Detection logic for new/unknown characters
- Event-specific configuration handling
- Input/output schema validation
"""

from detectmatelibrary.utils.persistency.component_interfaces import PersistConfig
from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.common._core_op._fit_logic import EnumState
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as schemas
from detectmatelibrary.utils.aux import time_test_mode
from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

# Set time test mode for consistent timestamps
time_test_mode()


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


class TestCharsetDetectorInitialization:
    """Test CharsetDetector initialization and configuration."""

    def test_default_initialization(self):
        """Test detector initialization with default parameters."""
        detector = CharsetDetector()

        assert detector.name == "CharsetDetector"
        assert hasattr(detector, 'config')
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema
        assert detector.output_schema == schemas.DetectorSchema
        assert hasattr(detector, 'persistency')

    def test_custom_config_initialization(self):
        """Test detector initialization with custom configuration."""
        detector = CharsetDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert hasattr(detector, 'persistency')
        assert isinstance(detector.persistency.events_data, dict)

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

    def test_register_persistency_was_called(self):
        """Main persistency should be registered so persist/load round-trips
        work."""
        cfg = CharsetDetectorConfig(
            persist=PersistConfig(path="memory://charset_regpersist/state")
        )
        detector = CharsetDetector(config=cfg)
        # _register_persistency builds a PersistencySaver bound to detector.persistency
        assert detector.saver is not None
        assert detector.saver._persistency is detector.persistency
        detector.saver.stop()


class TestCharsetDetectorTraining:
    """Test CharsetDetector training functionality."""

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        detector = CharsetDetector(config=config, name="MultipleDetector")
        # Train with multiple values (only event 1 should be tracked per config)
        for event in range(3):
            for level in ["INFO", "WARNING", "ERROR"]:
                parser_data = schemas.ParserSchema({
                    "parserType": "test",
                    "EventID": event,
                    "template": "test template",
                    "variables": ["0", "assa"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "logFormatVariables": {"level": level}
                })
                detector.train(parser_data)

        # Only event 1 should be tracked (based on events config)
        assert len(detector.persistency.events_data) == 1
        event_data = detector.persistency.get_event_data(1)
        assert event_data is not None
        # With expand_value=True, unique_set contains individual characters
        assert set("INFO") <= event_data["level"].unique_set
        assert set("WARNING") <= event_data["level"].unique_set
        assert set("ERROR") <= event_data["level"].unique_set
        assert set("assa") <= event_data["test"].unique_set


class TestCharsetDetectorDetection:
    """Test CharsetDetector detection functionality."""

    def test_detect_known_value_no_alert(self):
        detector = CharsetDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 12,
            "template": "test template",
            "variables": ["adsasddddddaaa"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.DetectorSchema()

        result = detector.detect(test_data, output)

        assert not result
        assert output.score == 0.0

    def test_detect_known_value_alert(self):
        detector = CharsetDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["asas", "adsd"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.DetectorSchema()

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

        train = schemas.ParserSchema({
            "parserType": "test", "EventID": 1, "template": "t",
            "variables": ["abc"], "logID": "1", "parsedLogID": "1",
            "parserID": "p", "log": "l", "logFormatVariables": {},
        })
        detector.train(train)

        # All known chars
        ok = schemas.ParserSchema({
            "parserType": "test", "EventID": 1, "template": "t",
            "variables": ["cba"], "logID": "2", "parsedLogID": "2",
            "parserID": "p", "log": "l", "logFormatVariables": {},
        })
        out = schemas.DetectorSchema()
        assert not detector.detect(ok, out)
        assert out.score == 0.0

        # Unknown chars 'x' and 'y'
        bad = schemas.ParserSchema({
            "parserType": "test", "EventID": 1, "template": "t",
            "variables": ["axy"], "logID": "3", "parsedLogID": "3",
            "parserID": "p", "log": "l", "logFormatVariables": {},
        })
        out = schemas.DetectorSchema()
        assert detector.detect(bad, out)
        assert out.score == 1.0
        assert any("'x'" in msg and "'y'" in msg for msg in out["alertsObtain"].values())


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

    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = CharsetDetector()

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.configure(log)
        detector.set_configuration()

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}


class TestCharsetDetectorAutoConfig:
    """Test that process() drives configure/set_configuration/train/detect
    automatically."""

    def test_audit_log_anomalies_via_process(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = CharsetDetector()

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        # Phase 1: configure — keep configuring for logs[:TRAIN_UNTIL]
        detector.fitlogic.config_state.current = EnumState.KEEP
        for log in logs[:TRAIN_UNTIL]:
            detector.process(log)

        # Transition: stop configure so next process() call triggers set_configuration()
        detector.fitlogic.config_state.current = EnumState.STOP

        # Phase 2: train — keep training for logs[:TRAIN_UNTIL]
        detector.fitlogic.train_state.current = EnumState.KEEP
        for log in logs[:TRAIN_UNTIL]:
            detector.process(log)

        # Phase 3: detect — stop training so process() only calls detect()
        detector.fitlogic.train_state.current = EnumState.STOP
        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            if detector.process(log) is not None:
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}


class TestCharsetDetectorGlobalInstances:
    """Tests event-ID-independent global instance detection."""

    def test_global_instance_detects_new_type(self):
        """Global instance monitoring Type detects CRED_REFR, USER_AUTH,
        USER_CMD which only appear after the training window (line 1800+)."""
        parser = MatcherParser(config=_PARSER_CONFIG)
        config_dict = {
            "detectors": {
                "CharsetDetector": {
                    "method_type": "charset_detector",
                    "auto_config": False,
                    "params": {},
                    "global": {
                        "test": {
                            "header_variables": [{"pos": "Type"}]
                        }
                    }
                }
            }
        }
        config = CharsetDetectorConfig.from_dict(config_dict, "CharsetDetector")
        detector = CharsetDetector(config=config)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        # Global tracker must be populated under the sentinel event ID
        assert GLOBAL_EVENT_ID in detector.persistency.get_events_data()

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                assert all(key.startswith("Global -") for key in output["alertsObtain"])
                detected_ids.add(log["logID"])

        assert len(detected_ids) > 0


class TestCharsetDetectorSetConfigurationPreservesPersist:
    def test_persist_flag_survives_set_configuration(self):
        detector = CharsetDetector()
        # Simulate persist being enabled by an earlier config load
        detector.config.persist = PersistConfig(path="memory://persist_flag/state")

        # Feed configure() with a couple of stable-variable samples
        for _ in range(5):
            sample = schemas.ParserSchema({
                "parserType": "test", "EventID": 1, "template": "t",
                "variables": ["abc"], "logID": "x", "parsedLogID": "x",
                "parserID": "p", "log": "l",
                "logFormatVariables": {"level": "INFO"},
            })
            detector.configure(sample)

        detector.set_configuration()

        assert detector.config.persist is not None
        assert detector.config.persist.path == "memory://persist_flag/state"
