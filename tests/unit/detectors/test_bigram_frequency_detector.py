"""Tests for BigramFrequencyDetector class.

This module tests the BigramFrequencyDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for unexpected values
- Event-specific configuration handling
- Input/output schema validation
"""

from detectmatelibrary.detectors.bigram_frequency_detector import BigramFrequencyDetector
import detectmatelibrary.schemas as sc
# Set time test mode for consistent timestamps
import pytest


pytestmark = pytest.mark.usefixtures("frozen_timestamps")


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


def _event_1_record(log_id: str, value: str) -> sc.ParserSchema:
    return sc.ParserSchema({
        "parserType": "test", "eventID": 1, "template": "test template", "variables": ["adsasd", value],
        "logID": log_id, "parsedLogID": log_id, "parserID": "test_parser", "log": "test log message",
        "headerVariables": {"level": "INFO"},
    })


class TestBigramFrequencyDetectorTraining:
    """Test BigramFrequencyDetector training functionality."""

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")
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
        # Check the level values
        assert "INFO" in event_data["level"].unique_set
        assert "WARNING" in event_data["level"].unique_set
        assert "ERROR" in event_data["level"].unique_set
        # Check the variable at position 1 (named "test")
        assert "assa" in event_data["test"].unique_set


class TestBigramFrequencyDetectorDetection:
    """Test BigramFrequencyDetector detection functionality."""

    def test_detect_ignores_unconfigured_event(self):
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")

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
            "variables": ["adsasd"],
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
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")
        detector.train(_event_1_record("1", "asdasd"))

        assert detector.detect(_event_1_record("2", "asdasd"), sc.DetectorSchema()) is False
        assert detector.detect(_event_1_record("3", "qwqwqw"), sc.DetectorSchema()) is True

    def test_detect_known_value_alert(self):
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")

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
            "variables": ["adsasd", "asdasd"],
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


def _parser_data(event_id, level, var_value):
    return sc.ParserSchema({
        "parserType": "test",
        "eventID": event_id,
        "template": "test template",
        "variables": ["0", var_value],
        "logID": "1",
        "parsedLogID": "1",
        "parserID": "test_parser",
        "log": "test log message",
        "headerVariables": {"level": level},
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
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["0"],  # only pos 0 — no value at pos 1
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "INFO"},
        })
        output = sc.DetectorSchema()
        # a missing variable is skipped: no TypeError and no alert
        assert detector.detect(test_data, output) is False

    def test_default_freqs_false_does_not_consult_fallback(self):
        """default_freqs=False (the default): no fallback consultation."""
        detector = BigramFrequencyDetector(config=config, name="MultipleDetector")
        assert detector.config.default_freqs is False
        # Train a tracker on a value with no overlap to English text
        detector.train(_parser_data(1, "INFO", "qqq"))

        # Detect a typical English-looking value. Without fallback, sparse
        # per-var table → low prob → alert expected.
        test_data = _parser_data(1, "INFO", "the")
        output = sc.DetectorSchema()
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
        output = sc.DetectorSchema()
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
        parser_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["abc", "xyz"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {},
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
