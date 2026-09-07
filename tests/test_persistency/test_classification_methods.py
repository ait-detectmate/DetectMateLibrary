"""Tests for the classification-method selection model."""

import pytest
from pydantic import ValidationError

from detectmatelibrary.utils.persistency.event_data_structures.trackers import (
    ClassificationMethods,
)


class TestDefaults:
    def test_default_is_index_only_under_consensus(self):
        """The default must reproduce the historical behaviour exactly."""
        m = ClassificationMethods()
        assert (m.index, m.time, m.slope_index, m.slope_time) == (True, False, False, False)
        assert m.decision == "consensus"
        assert m.slope_threshold == -0.05

    def test_enabled_lists_names_in_block_order(self):
        m = ClassificationMethods(index=True, time=True, slope_index=False, slope_time=True)
        assert m.enabled == ("index", "time", "slope_time")

    def test_enabled_of_a_single_method(self):
        m = ClassificationMethods(index=False, slope_time=True)
        assert m.enabled == ("slope_time",)


class TestNeedsTimestamps:
    @pytest.mark.parametrize(
        "kwargs, expected",
        [
            ({}, False),
            ({"index": False, "slope_index": True}, False),
            ({"index": False, "time": True}, True),
            ({"index": False, "slope_time": True}, True),
            ({"time": True, "slope_time": True}, True),
        ],
    )
    def test_only_the_time_axis_methods_need_stamps(self, kwargs, expected):
        assert ClassificationMethods(**kwargs).needs_timestamps is expected


class TestValidation:
    def test_no_method_enabled_is_rejected(self):
        """A method-less config would silently classify every surviving
        variable STABLE, because INSUFFICIENT_DATA / STATIC / RANDOM are
        decided before any method is consulted."""
        with pytest.raises(ValidationError, match="at least one classification method"):
            ClassificationMethods(index=False)

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            ClassificationMethods(segmentation="both")

    def test_unknown_decision_is_rejected(self):
        with pytest.raises(ValidationError):
            ClassificationMethods(decision="unanimous")

    @pytest.mark.parametrize("rule", ["consensus", "majority"])
    def test_both_decision_rules_are_accepted(self, rule):
        assert ClassificationMethods(decision=rule).decision == rule


def test_round_trips_through_a_plain_dict():
    """to_state() and the config layer both move this model as a dict."""
    m = ClassificationMethods(
        index=False, time=True, slope_time=True, slope_threshold=-0.2, decision="majority"
    )
    assert ClassificationMethods(**m.model_dump()) == m
