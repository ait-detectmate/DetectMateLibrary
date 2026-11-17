"""Contract of the auto-config detectors: set_configuration() writes only its
outputs (AGENTS.md, "Write only your outputs in set_configuration()").

Every config field other than the configure phase's outputs is operator
input and must read back unchanged after the phase. The parametrized checks
run for AUTO_CONFIG_DETECTORS in tests/contract/registry.py.
"""
import logging

import pytest

from detectmatelibrary import detectors
from tests.contract.registry import AUTO_CONFIG_DETECTORS, cases, parsed_log

# what the configure phase may write (EventSequence picks a window length)
OUTPUTS = {"events", "auto_config", "fixed_window_size"}

# non-default inputs of each detector's configure phase, so that a reset would show
_VARIABLE_AUTO = {
    "use_stable_vars": False, "use_static_vars": False,
    "classification": {"index": False, "time": True, "slope_index": True},
    "timestamp_variable": "level", "timestamp_format": "%y%m%d %H%M%S",
}
AUTO_CONFIG_PARAMS = {
    detectors.NewValueDetector: _VARIABLE_AUTO,
    detectors.NewValueComboDetector: {**_VARIABLE_AUTO, "max_combo_size": 2},
    detectors.CharsetDetector: _VARIABLE_AUTO,
    detectors.ValueRangeDetector: _VARIABLE_AUTO,
    detectors.BigramFrequencyDetector: _VARIABLE_AUTO,
    detectors.NewEventDetector: None,  # its configure phase has no inputs
    detectors.EventSequenceDetector: {"min_window_size": 2, "max_window_size": 4},
}
# NewEvent keys on EventIDs only: an empty events block is its normal output
SELECTING_VARIABLES = [case for case in AUTO_CONFIG_DETECTORS if case.cls is not detectors.NewEventDetector]


def _stream(n: int, stable: bool = True) -> list:
    """Events 1 and 2 alternating with the same variables (stable), or a new
    event with new variables every time (nothing to select), each with a
    timestamp."""
    records = [parsed_log(i, 1 + i % 2, ("alice", "10.0.0.1")) if stable
               else parsed_log(i, 100 + i, (f"user{i}", f"10.0.0.{i}")) for i in range(n)]
    for i, record in enumerate(records):
        record["headerVariables"].update({"level": f"081109 2036{i:02d}", "blk": "session"})
    return records


def _auto_configured(case, **params):
    """The case's detector with auto_config on, its events left to the
    configure phase, and non-default operator settings."""
    config = case.yaml(persist={"path": "memory://contract/auto"}, **params)
    entry = config["detectors"][case.name]
    entry["auto_config"] = True
    entry.pop("events", None)
    entry["params"].pop("fixed_window_size", None)  # EventSequence: the configure phase picks it
    if AUTO_CONFIG_PARAMS[case.cls] is not None:
        entry["auto_config_params"] = AUTO_CONFIG_PARAMS[case.cls]
    return case.cls(name=case.name, config=config)


def test_every_auto_config_detector_has_its_inputs_listed():
    assert {case.cls for case in AUTO_CONFIG_DETECTORS} == set(AUTO_CONFIG_PARAMS)


@pytest.mark.parametrize("stable", [True, False], ids=["stable", "nothing_stable"])
@pytest.mark.parametrize("case", cases(AUTO_CONFIG_DETECTORS))
def test_configure_phase_changes_only_its_outputs(case, stable):
    operator_settings = {
        "parser": "parser", "data_use_configure": 20, "data_use_training": 17, "start_id": 99,
        "use_config_data_as_training": False, "connector_name": "Verification", "connector_url": "url",
        **({"session_variable": "blk"} if case.session else {}),
    }
    with _auto_configured(case, **operator_settings) as detector:
        before = detector.config.model_dump()
        for record in _stream(21, stable):  # the 21st record ends the configure phase
            detector.process(record)
        after = detector.config.model_dump()

    assert after["auto_config"] is False
    assert {name for name in before if before[name] != after[name]} <= OUTPUTS


@pytest.mark.parametrize("case", cases(AUTO_CONFIG_DETECTORS))
def test_without_auto_config_the_configure_phase_changes_nothing(case):
    detector = case.build(data_use_configure=20, data_use_training=1)
    before = detector.config.model_dump()
    for record in _stream(21):
        detector.process(record)
    assert detector.config.model_dump() == before


@pytest.mark.parametrize("case", cases(SELECTING_VARIABLES))
def test_empty_configure_phase_warns(case, caplog):
    with _auto_configured(case) as detector, caplog.at_level(logging.WARNING):
        detector.set_configuration()

    assert any("empty configuration" in record.message for record in caplog.records)
    assert detector.config.auto_config is False


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="B1: set_configuration() changes the default config all new detectors share")
@pytest.mark.parametrize("case", cases(AUTO_CONFIG_DETECTORS))
def test_configuring_one_detector_leaves_new_ones_unconfigured(case):
    case.cls().set_configuration()
    assert case.cls().config.auto_config is True
