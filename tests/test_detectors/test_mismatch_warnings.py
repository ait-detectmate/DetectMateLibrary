"""Tests for config-data mismatch warnings in detectors.

Covers two warning levels:
1. Configured EventID never seen in training data.
2. EventID seen in training data but configured variables not extracted.

Also covers the auto_config=True empty-config warning.
"""

import logging
import pytest
import detectmatelibrary.schemas as schemas
from detectmatelibrary.detectors.new_value_detector import NewValueDetector
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector


def _make_parser_schema(
    event_id: int,
    variables: list,
    log_format_variables: dict,
) -> schemas.ParserSchema:
    return schemas.ParserSchema({
        "parserType": "test",
        "EventID": event_id,
        "template": "test template",
        "variables": variables,
        "logID": "1",
        "parsedLogID": "1",
        "parserID": "test_parser",
        "log": "test log message",
        "logFormatVariables": log_format_variables,
    })


# ---- Config fixtures --------------------------------------------------------

def _nvd_config(event_id: int, pos: int = 0, header: str | None = None) -> dict:
    """Build a minimal NewValueDetector config targeting one variable."""
    instance: dict = {"params": {}}
    if header is not None:
        instance["header_variables"] = [{"pos": header, "params": {}}]
    else:
        instance["variables"] = [{"pos": pos, "name": f"var_{pos}", "params": {}}]
    return {
        "detectors": {
            "TestDetector": {
                "method_type": "new_value_detector",
                "auto_config": False,
                "params": {},
                "events": {event_id: {"inst": instance}},
            }
        }
    }


# ---- NewValueDetector warning tests -----------------------------------------

class TestNewValueDetectorMismatchWarnings:

    def test_warn_event_id_never_seen(self, caplog: pytest.LogCaptureFixture) -> None:
        """Warn when configured EventID is not present in training data at
        all."""
        detector = NewValueDetector(name="TestDetector", config=_nvd_config(event_id=99))
        # Train on EventID=1 only — EventID=99 is never seen
        for _ in range(3):
            detector.train(_make_parser_schema(1, ["val"], {"status": "ok"}))

        with caplog.at_level(logging.WARNING):
            detector.post_train()

        assert any("99" in r.message and "never observed" in r.message for r in caplog.records)

    def test_warn_event_id_seen_but_no_variables_extracted(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warn when EventID is seen but configured positional variable is out
        of bounds."""
        # Config expects var at position 0, but data has empty variables list
        detector = NewValueDetector(name="TestDetector", config=_nvd_config(event_id=1, pos=0))
        for _ in range(3):
            # EventID=1 IS seen, but variables=[] so get_configured_variables returns {}
            detector.train(_make_parser_schema(1, [], {"status": "ok"}))

        with caplog.at_level(logging.WARNING):
            detector.post_train()

        assert any(
            "1" in r.message and "no configured variables were extracted" in r.message
            for r in caplog.records
        )

    def test_warn_header_variable_not_in_log_format(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warn when EventID is seen but configured header_variable key is
        absent."""
        # Config expects header 'Time', but data has only 'status'
        detector = NewValueDetector(
            name="TestDetector", config=_nvd_config(event_id=1, header="Time")
        )
        for _ in range(3):
            detector.train(_make_parser_schema(1, [], {"status": "ok"}))

        with caplog.at_level(logging.WARNING):
            detector.post_train()

        assert any("no configured variables were extracted" in r.message for r in caplog.records)

    def test_no_warning_when_config_matches_data(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No warning when configured variables are correctly extracted during
        training."""
        detector = NewValueDetector(
            name="TestDetector", config=_nvd_config(event_id=1, header="status")
        )
        for _ in range(3):
            detector.train(_make_parser_schema(1, [], {"status": "ok"}))

        with caplog.at_level(logging.WARNING):
            detector.post_train()

        assert not any(r.levelno == logging.WARNING for r in caplog.records)

    def test_auto_config_skips_mismatch_check(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """post_train() does not run coverage check for auto_config=True
        detectors."""
        detector = NewValueDetector()  # auto_config=True by default
        # Train on some data — no mismatch check should fire because auto_config=True
        for _ in range(3):
            detector.train(_make_parser_schema(1, ["x"], {"status": "ok"}))

        with caplog.at_level(logging.WARNING):
            detector.post_train()

        mismatch_warnings = [
            r for r in caplog.records
            if "never observed" in r.message or "no configured variables" in r.message
        ]
        assert not mismatch_warnings

    def test_auto_config_empty_config_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warn in set_configuration() when auto_config produces an empty
        events config."""
        detector = NewValueDetector()
        # configure() with no data → auto_conf_persistency is empty → empty config
        with caplog.at_level(logging.WARNING):
            detector.set_configuration()

        assert any("empty configuration" in r.message for r in caplog.records)


# ---- NewValueComboDetector warning tests ------------------------------------

class TestNewValueComboDetectorMismatchWarnings:

    def test_warn_event_id_never_seen(self, caplog: pytest.LogCaptureFixture) -> None:
        """Warn when configured EventID is not present in combo detector
        training data."""
        config = {
            "detectors": {
                "ComboDetector": {
                    "method_type": "new_value_combo_detector",
                    "auto_config": False,
                    "params": {},
                    "events": {
                        99: {
                            "inst": {
                                "params": {},
                                "header_variables": [{"pos": "status", "params": {}}],
                            }
                        }
                    },
                }
            }
        }
        detector = NewValueComboDetector(name="ComboDetector", config=config)
        for _ in range(3):
            detector.train(_make_parser_schema(1, ["val"], {"status": "ok"}))

        with caplog.at_level(logging.WARNING):
            detector.post_train()

        assert any("99" in r.message and "never observed" in r.message for r in caplog.records)

    def test_no_warning_when_config_matches(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No warning when combo detector config matches training data."""
        config = {
            "detectors": {
                "ComboDetector": {
                    "method_type": "new_value_combo_detector",
                    "auto_config": False,
                    "params": {},
                    "events": {
                        1: {
                            "inst": {
                                "params": {},
                                "header_variables": [{"pos": "status", "params": {}}],
                            }
                        }
                    },
                }
            }
        }
        detector = NewValueComboDetector(name="ComboDetector", config=config)
        for _ in range(3):
            detector.train(_make_parser_schema(1, [], {"status": "ok"}))

        with caplog.at_level(logging.WARNING):
            detector.post_train()

        assert not any(r.levelno == logging.WARNING for r in caplog.records)
