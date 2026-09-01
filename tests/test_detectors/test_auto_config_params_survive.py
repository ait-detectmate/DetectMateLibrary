"""set_configuration writes only its outputs.

Every field on a detector config other than `events` and `auto_config` is
operator input and must read back unchanged after the configure phase. This
is the regression test for auto-config inputs being silently reset.
"""

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
from detectmatelibrary.common.variable_detector import VariableAutoConfigParams


def _schema(event_id: int, level: str, log_id: str):
    return {
        "logID": log_id,
        "EventID": event_id,
        "template": "user <*> from <*>",
        "variables": ["alice", "10.0.0.1"],
        "logFormatVariables": {"user": "alice", "src": "10.0.0.1", "level": level},
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
