"""Tests for detectmatelibrary.base_detectors._variable_hooks."""
import pytest

from detectmatelibrary.base_detectors._variable_hooks import VariableHooks


class FlagBad(VariableHooks):
    name = "Probe"

    def _check_variable(self, tracker, value, key):
        return f"{key} is bad" if value == "bad" else None


class EventTracker:
    def __init__(self, names):
        self._data = {name: object() for name in names}

    def get_data(self):
        return self._data


def test_defaults_leave_variables_alone_and_describe_the_detector():
    hooks = FlagBad()
    assert hooks._prepare_variables({"a": 1}, stage="training") == {"a": 1}
    assert hooks._description() == "Probe detected anomalies."


def test_check_variable_must_be_overridden():
    with pytest.raises(NotImplementedError):
        VariableHooks()._check_variable(tracker=None, value=1, key="a")


def test_alert_keys_name_the_event_or_the_global_scope():
    hooks = FlagBad()
    assert hooks._alert_key(3, "user", is_global=False) == "EventID 3 - user"
    assert hooks._alert_key(3, "Level", is_global=True) == "Global - Level"


def test_check_event_scores_one_per_anomalous_variable():
    alerts: dict = {}
    score = FlagBad()._check_event(
        alerts, event_id=1, event_tracker=EventTracker(["user", "host", "missing"]),
        variables={"user": "bad", "host": "bad", "other": "bad"}, is_global=False)

    assert score == 2.0
    assert alerts == {"EventID 1 - user": "user is bad", "EventID 1 - host": "host is bad"}
