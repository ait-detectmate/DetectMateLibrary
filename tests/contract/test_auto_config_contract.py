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
from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.detectors.event_sequence_detector import (
    EventSequenceDetector,
    EventSequenceDetectorConfig,
    SequenceAutoConfigParams,
)
from detectmatelibrary.detectors.new_event_detector import (
    NewEventDetector,
    NewEventDetectorConfig,
)
from detectmatelibrary.detectors.new_value_combo_detector import (
    ComboAutoConfigParams,
    NewValueComboDetector,
    NewValueComboDetectorConfig,
)
from detectmatelibrary.detectors.new_value_detector import (
    NewValueDetector,
    NewValueDetectorConfig,
)
from detectmatelibrary.base_detectors import VariableAutoConfigParams
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


def _stream(n: int) -> list:
    """Events 1 and 2 alternating, with the same variables and a timestamp."""
    records = [parsed_log(i, 1 + i % 2, ("alice", "10.0.0.1")) for i in range(n)]
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


@pytest.mark.parametrize("case", cases(AUTO_CONFIG_DETECTORS))
def test_configure_phase_changes_only_its_outputs(case):
    operator_settings = {
        "parser": "parser", "data_use_configure": 20, "data_use_training": 17, "start_id": 99,
        "use_config_data_as_training": False, "connector_name": "Verification", "connector_url": "url",
        **({"session_variable": "blk"} if case.session else {}),
    }
    with _auto_configured(case, **operator_settings) as detector:
        before = detector.config.model_dump()
        for record in _stream(21):  # the 21st record ends the configure phase
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


# ---- per-detector tests, sorted out in the next commit ----------------------------


def _schema(event_id: int, level: str, log_id: str):
    return {
        "logID": log_id,
        "eventID": event_id,
        "template": "user <*> from <*>",
        "variables": ["alice", "10.0.0.1"],
        "headerVariables": {"user": "alice", "src": "10.0.0.1", "level": level},
    }


_AUTO = dict(
    use_stable_vars=True,
    use_static_vars=True,
    classification=dict(index=False, time=True, slope_index=True),
    timestamp_variable="level",
    timestamp_format="%y%m%d %H%M%S",
)

_STREAM = [_schema(1, f"081109 2036{i:02d}", str(i)) for i in range(20)]


def _assert_auto_params_intact(config):
    auto = config.auto_config_params
    assert auto.use_stable_vars is True
    assert auto.use_static_vars is True
    assert auto.classification.enabled == ("time", "slope_index")
    assert auto.timestamp_variable == "level"
    assert auto.timestamp_format == "%y%m%d %H%M%S"


def test_new_value_detector_keeps_auto_config_params():
    detector = NewValueDetector(
        name="NewValueDetector",
        config=NewValueDetectorConfig(
            parser="MyParser",
            auto_config_params=VariableAutoConfigParams(**_AUTO),
        ),
    )
    for record in _STREAM:
        detector.configure(record)
    detector.set_configuration()

    _assert_auto_params_intact(detector.config)
    assert detector.config.parser == "MyParser"
    assert detector.config.auto_config is False
    assert isinstance(detector.config.events, EventsConfig)


def test_combo_detector_keeps_auto_config_params():
    detector = NewValueComboDetector(
        name="NewValueComboDetector",
        config=NewValueComboDetectorConfig(
            parser="MyParser",
            auto_config_params=ComboAutoConfigParams(**_AUTO),
        ),
    )
    for record in _STREAM:
        detector.configure(record)
    detector.set_configuration()

    _assert_auto_params_intact(detector.config)
    assert detector.config.parser == "MyParser"
    assert detector.config.auto_config is False
    assert isinstance(detector.config.events, EventsConfig)


def test_new_event_detector_keeps_operator_settings():
    detector = NewEventDetector(
        name="NewEventDetector",
        config=NewEventDetectorConfig(parser="MyParser", data_use_training=17),
    )
    for record in _STREAM:
        detector.configure(record)
    detector.set_configuration()

    assert detector.config.parser == "MyParser"
    assert detector.config.data_use_training == 17
    assert detector.config.auto_config is False
    assert isinstance(detector.config.events, EventsConfig)


def test_event_sequence_detector_keeps_operator_settings():
    # Same shape as test_unstable_stream_generates_no_instance in
    # test_event_sequence_detector.py: every EventID is unique, so every
    # candidate window fills and clears min_samples but its sequences never
    # repeat -- no candidate is ever classified STABLE/STATIC. That drives
    # the no-stable-candidate early-return branch this task rewrote, which
    # is the widest-blast-radius site: it is not a VariableDetector, so
    # before this task it restored only `persist` by hand and silently
    # reset every other operator field.
    detector = EventSequenceDetector(
        name="EventSequenceDetector",
        config=EventSequenceDetectorConfig(
            parser="MyParser",
            data_use_configure=5,
            data_use_training=1,
            use_config_data_as_training=False,
            auto_config_params=SequenceAutoConfigParams(
                min_window_size=3,
                max_window_size=6,
            ),
        ),
    )
    for i, event_id in enumerate(range(40)):
        detector.configure(_schema(event_id, "081109 203600", str(i)))
    detector.set_configuration()

    assert detector.config.fixed_window_size is None
    assert detector.config.parser == "MyParser"
    assert detector.config.data_use_configure == 5
    assert detector.config.data_use_training == 1
    assert detector.config.use_config_data_as_training is False
    assert detector.config.auto_config_params.min_window_size == 3
    assert detector.config.auto_config_params.max_window_size == 6
    assert detector.config.auto_config is False
    assert isinstance(detector.config.events, EventsConfig)


def test_event_sequence_detector_keeps_auto_config_params():
    """The sequence detector writes fixed_window_size, not a fresh config."""
    from detectmatelibrary.detectors.event_sequence_detector import (
        EventSequenceDetector,
        EventSequenceDetectorConfig,
        SequenceAutoConfigParams,
    )

    detector = EventSequenceDetector(
        name="EventSequenceDetector",
        config=EventSequenceDetectorConfig(
            parser="MyParser",
            auto_config_params=SequenceAutoConfigParams(
                min_window_size=2, max_window_size=4
            ),
        ),
    )
    for record in _STREAM:
        detector.configure(record)
    detector.set_configuration()

    auto = detector.config.auto_config_params
    assert auto.min_window_size == 2
    assert auto.max_window_size == 4
    assert detector.config.parser == "MyParser"
    assert detector.config.fixed_window_size == 4
    assert detector.config.auto_config is False
    assert isinstance(detector.config.events, EventsConfig)
