"""Tests for BigramFrequencyDetector class.

This module tests the BigramFrequencyDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for unexpected values
- Event-specific configuration handling
- Input/output schema validation
"""

from detectmatelibrary.common._core_op._fit_logic import TrainState
from detectmatelibrary.detectors.bigram_frequency_detector import (
    BigramFrequencyDetector, BigramFrequencyDetectorConfig, BufferMode
)
from detectmatelibrary.common._core_op._fit_logic import ConfigState
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as schemas
from detectmatelibrary.utils.aux import time_test_mode
from detectmatelibrary_tests.test_pipelines.test_configuration_engine import AUDIT_LOG
# Set time test mode for consistent timestamps
time_test_mode()


_SKIP_REPETITIONS_CONFIG = {
    "detectors": {
        "MultipleDetector": {
            "method_type": "bigram_frequency_detector",
            "auto_config": False,
            "params": {"skip_repetitions": True},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{"pos": 1, "name": "test", "params": {}}],
                        "header_variables": [{"pos": "level", "params": {}}],
                    }
                }
            },
        }
    }
}


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "bigram_frequency_detector",
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
            "method_type": "bigram_frequency_detector",
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


class TestBigramFrequencyDetectorInitialization:
    """Test BigramFrequencyDetector initialization and configuration."""

    def test_default_initialization(self):
        """Test detector initialization with default parameters."""
        detector = BigramFrequencyDetector()

        assert detector.name == "BigramFrequencyDetector"
        assert hasattr(detector, 'config')
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema
        assert detector.output_schema == schemas.DetectorSchema
        assert hasattr(detector, 'persistency')

    def test_custom_config_initialization(self):
        """Test detector initialization with custom configuration."""
        detector = BigramFrequencyDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert hasattr(detector, 'persistency')
        assert isinstance(detector.persistency.events_data, dict)


class TestBigramFrequencyDetectorTraining:
    """Test BigramFrequencyDetector training functionality."""

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")
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
        # Check the level values
        assert "INFO" in event_data["level"].unique_set
        assert "WARNING" in event_data["level"].unique_set
        assert "ERROR" in event_data["level"].unique_set
        # Check the variable at position 1 (named "test")
        assert "assa" in event_data["test"].unique_set


class TestBigramFrequencyDetectorDetection:
    """Test BigramFrequencyDetector detection functionality."""

    def test_detect_known_value_no_alert(self):
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")

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
            "variables": ["adsasd"],
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
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")

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
            "variables": ["adsasd", "asdasd"],
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
                "path_templates": "detectmatelibrary_tests/test_folder/audit_templates.txt",
            },
        }
    }
}


class TestBigramFrequencyDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = BigramFrequencyDetector()

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:1800]:
            detector.configure(log)
        detector.set_configuration()

        for log in logs[:1800]:
            detector.train(log)

        detected_ids: set[str] = set()
        for log in logs[1800:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}


class TestBigramFrequencyDetectorAutoConfig:
    """Test that process() drives configure/set_configuration/train/detect
    automatically."""

    def test_audit_log_anomalies_via_process(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = BigramFrequencyDetector()

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        # Phase 1: configure — keep configuring for logs[:1800]
        detector.fitlogic.configure_state = ConfigState.KEEP_CONFIGURE
        for log in logs[:1800]:
            detector.process(log)

        # Transition: stop configure so next process() call triggers set_configuration()
        detector.fitlogic.configure_state = ConfigState.STOP_CONFIGURE

        # Phase 2: train — keep training for logs[:1800]
        detector.fitlogic.train_state = TrainState.KEEP_TRAINING
        for log in logs[:1800]:
            detector.process(log)

        # Phase 3: detect — stop training so process() only calls detect()
        detector.fitlogic.train_state = TrainState.STOP_TRAINING
        detected_ids: set[str] = set()
        for log in logs[1800:]:
            if detector.process(log) is not None:
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}


class TestBigramFrequencyDetectorGlobalInstances:
    """Tests event-ID-independent global instance detection."""

    def test_global_instance_detects_new_type(self):
        """Global instance monitoring Type detects CRED_REFR, USER_AUTH,
        USER_CMD which only appear after the training window (line 1800+)."""
        parser = MatcherParser(config=_PARSER_CONFIG)
        config_dict = {
            "detectors": {
                "BigramFrequencyDetector": {
                    "method_type": "bigram_frequency_detector",
                    "prob_thresh": 0.2,
                    "auto_config": False,
                    "global": {
                        "test": {
                            "header_variables": [{"pos": "Type"}]
                        }
                    }
                }
            }
        }
        config = BigramFrequencyDetectorConfig.from_dict(config_dict, "BigramFrequencyDetector")
        detector = BigramFrequencyDetector(config=config)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:1800]:
            detector.train(log)

        # Global tracker must be populated under the sentinel event ID
        assert GLOBAL_EVENT_ID in detector.persistency.get_events_data()

        detected_ids: set[str] = set()
        for log in logs[1800:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                assert all(key.startswith("Global -") for key in output["alertsObtain"])
                detected_ids.add(log["logID"])

        assert len(detected_ids) > 0


class TestBigramFrequencyDetectorPersistencyRegistration:
    def test_register_persistency_is_called(self):
        """Persistency must be registered so `persist:` config takes effect."""
        from unittest.mock import patch

        with patch.object(
            BigramFrequencyDetector,
            "_register_persistency",
            autospec=True,
        ) as mock_reg:
            detector = BigramFrequencyDetector()

        mock_reg.assert_called_once()
        _, called_persistency = mock_reg.call_args[0]  # (self, persistency)
        assert called_persistency is detector.persistency


class TestBigramFrequencyDetectorSetConfigurationPersist:
    def test_set_configuration_preserves_persist(self):
        """Auto-config must not silently drop the persist sub-config."""
        from detectmatelibrary.common.detector import PersistConfig
        detector = BigramFrequencyDetector()
        sentinel_persist = PersistConfig(path="/tmp/sentinel")
        detector.config.persist = sentinel_persist
        detector.set_configuration()
        assert detector.config.persist == sentinel_persist


def _parser_data(event_id, level, var_value):
    return schemas.ParserSchema({
        "parserType": "test",
        "EventID": event_id,
        "template": "test template",
        "variables": ["0", var_value],
        "logID": "1",
        "parsedLogID": "1",
        "parserID": "test_parser",
        "log": "test log message",
        "logFormatVariables": {"level": level},
    })


class TestBigramFrequencyDetectorTrainBugFixes:
    def test_first_occurrence_of_new_event_is_trained(self):
        """Review #4: the very first training call for a new EventID must
        update the per-variable freq table."""
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")
        detector.train(_parser_data(1, "INFO", "abc"))

        event_data = detector.persistency.get_event_data(1)
        # 'test' is the variable at pos 1, configured in `config` fixture
        tracker = event_data["test"]
        freq = tracker.extra_state.get("freq", {})
        # "abc" produces bigrams: (-1,'a'), ('a','b'), ('b','c'), ('c',-1)
        assert "a" in freq
        assert "b" in freq["a"]
        assert freq["a"]["b"] == 1

    def test_skip_repetitions_does_not_skip_first_occurrence(self):
        """skip_repetitions must train on the first occurrence of a value even
        when the event was just registered."""
        detector = BigramFrequencyDetector(config=_SKIP_REPETITIONS_CONFIG, name="MultipleDetector")
        detector.train(_parser_data(1, "INFO", "abc"))

        tracker = detector.persistency.get_event_data(1)["test"]
        freq = tracker.extra_state.get("freq", {})
        # First occurrence must still be trained: "abc" should produce the bigrams above
        assert freq.get("a", {}).get("b") == 1

    def test_skip_repetitions_skips_repeat_value(self):
        """A repeated value with skip_repetitions=True must not double-count
        bigrams."""
        detector = BigramFrequencyDetector(config=_SKIP_REPETITIONS_CONFIG, name="MultipleDetector")
        detector.train(_parser_data(1, "INFO", "abc"))
        detector.train(_parser_data(1, "INFO", "abc"))  # same value

        tracker = detector.persistency.get_event_data(1)["test"]
        freq = tracker.extra_state.get("freq", {})
        # Only one training pass should have happened: ('a','b') count is 1, not 2
        assert freq.get("a", {}).get("b") == 1


class TestBigramFrequencyDetectorDetectFixes:
    def test_detect_helper_survives_missing_variable(self):
        """Review #5: variables.get(var_name) returning None must not raise."""
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")
        # Train so the tracker for var 'test' exists
        detector.train(_parser_data(1, "INFO", "abc"))

        # Detect with a parser line that lacks the 'test' variable
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["0"],  # only pos 0 — no value at pos 1
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"},
        })
        output = schemas.DetectorSchema()
        # Must not raise TypeError
        result = detector.detect(test_data, output)
        assert isinstance(result, bool)

    def test_default_freqs_false_does_not_consult_fallback(self):
        """default_freqs=False (the default): no fallback consultation."""
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")
        assert detector.config.default_freqs is False
        # Train a tracker on a value with no overlap to English text
        detector.train(_parser_data(1, "INFO", "qqq"))

        # Detect a typical English-looking value. Without fallback, sparse
        # per-var table → low prob → alert expected.
        test_data = _parser_data(1, "INFO", "the")
        output = schemas.DetectorSchema()
        result = detector.detect(test_data, output)
        assert result is True

    def test_default_freqs_true_consults_fallback(self):
        """default_freqs=True: when the per-var table misses, fall back to the
        English bigram table — common English bigrams should not alert."""
        cfg = {
            "detectors": {
                "MultipleDetector": {
                    "method_type": "bigram_frequency_detector",
                    "auto_config": False,
                    "params": {"default_freqs": True, "prob_thresh": 0.001},
                    "events": {
                        1: {
                            "test": {
                                "params": {},
                                "variables": [{"pos": 1, "name": "test", "params": {}}],
                                "header_variables": [{"pos": "level", "params": {}}],
                            }
                        }
                    },
                }
            }
        }
        detector = BigramFrequencyDetector(config=cfg, name="MultipleDetector")
        # Train so the tracker exists (with sparse data — fallback will dominate)
        detector.train(_parser_data(1, "INFO", "x"))

        # Detect a common English word — fallback should produce non-zero probs
        test_data = _parser_data(1, "INFO", "the")
        output = schemas.DetectorSchema()
        result = detector.detect(test_data, output)
        assert result is False


class TestBigramFrequencyDetectorPersistenceRoundTrip:
    def test_freq_table_survives_save_and_load(self):
        """The learned bigram model must round-trip through
        PersistencySaver."""
        base_path = "memory://bigram_roundtrip/state"

        cfg_dict = {
            "detectors": {
                "MultipleDetector": {
                    "method_type": "bigram_frequency_detector",
                    "auto_config": False,
                    "persist": {"path": base_path},
                    "params": {},
                    "events": {
                        1: {
                            "test": {
                                "params": {},
                                "variables": [{"pos": 1, "name": "test", "params": {}}],
                                "header_variables": [{"pos": "level", "params": {}}],
                            }
                        }
                    },
                }
            }
        }
        det1 = BigramFrequencyDetector(config=cfg_dict, name="MultipleDetector")
        det1.train(_parser_data(1, "INFO", "abc"))
        det1.train(_parser_data(1, "INFO", "abd"))
        assert det1.saver is not None
        det1.saver.save()
        det1.saver.stop()

        cfg_dict_reload = {
            "detectors": {
                "MultipleDetector": {
                    "method_type": "bigram_frequency_detector",
                    "auto_config": False,
                    "persist": {"path": base_path, "auto_load": True},
                    "params": {},
                    "events": {
                        1: {
                            "test": {
                                "params": {},
                                "variables": [{"pos": 1, "name": "test", "params": {}}],
                                "header_variables": [{"pos": "level", "params": {}}],
                            }
                        }
                    },
                }
            }
        }
        det2 = BigramFrequencyDetector(config=cfg_dict_reload, name="MultipleDetector")

        a_tracker = det1.persistency.get_event_data(1)["test"]
        b_tracker = det2.persistency.get_event_data(1)["test"]
        assert b_tracker.extra_state.get("freq") == a_tracker.extra_state.get("freq")
        assert b_tracker.extra_state.get("total_freq") == a_tracker.extra_state.get("total_freq")
        det2.saver.stop()


class TestBigramFrequencyDetectorPerVarIsolation:
    def test_two_variables_have_independent_freq_tables(self):
        """Training on one variable must not affect another variable's
        table."""
        cfg = {
            "detectors": {
                "TwoVarDetector": {
                    "method_type": "bigram_frequency_detector",
                    "auto_config": False,
                    "params": {},
                    "events": {
                        1: {
                            "test": {
                                "params": {},
                                "variables": [
                                    {"pos": 0, "name": "a", "params": {}},
                                    {"pos": 1, "name": "b", "params": {}},
                                ],
                            }
                        }
                    },
                }
            }
        }
        detector = BigramFrequencyDetector(config=cfg, name="TwoVarDetector")
        parser_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["abc", "xyz"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {},
        })
        detector.train(parser_data)

        a_tracker = detector.persistency.get_event_data(1)["a"]
        b_tracker = detector.persistency.get_event_data(1)["b"]
        a_freq = a_tracker.extra_state["freq"]
        b_freq = b_tracker.extra_state["freq"]

        # 'a' learned bigrams from "abc": (a,b), (b,c), plus boundaries
        assert "a" in a_freq and "b" in a_freq["a"]
        # 'b' should NOT have learned anything from "abc"
        assert "a" not in b_freq
        # 'b' DID learn from "xyz"
        assert "x" in b_freq and "y" in b_freq["x"]
