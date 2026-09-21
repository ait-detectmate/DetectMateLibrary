"""Tests for the classification-method selection model."""

import math

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


class TestSegmentThresholds:
    def test_default_reproduces_the_historical_list(self):
        assert ClassificationMethods().segment_thresholds == [1.1, 0.3, 0.1, 0.01]

    def test_default_instances_do_not_share_a_list(self):
        """default_factory, not a literal: a shared list would let one
        instance's in-place edit leak into every other."""
        a, b = ClassificationMethods(), ClassificationMethods()
        assert a.segment_thresholds is not b.segment_thresholds

    def test_field_sits_between_time_and_slope_index(self):
        """The block reads primitive by primitive: the two segment methods
        and their thresholds, then the two slope methods and theirs."""
        assert list(ClassificationMethods().model_dump()) == [
            "index", "time", "segment_thresholds",
            "slope_index", "slope_time", "slope_threshold", "decision",
        ]

    @pytest.mark.parametrize(
        "bad, message",
        [
            ([], "at least one segment threshold"),
            ([1.1, 0.0], "must be positive"),
            ([1.1, -0.3], "must be positive"),
            ([1.1, math.inf], "must be finite"),
            ([math.nan, 0.3], "must be finite"),
        ],
    )
    def test_rejected_lists(self, bad, message):
        with pytest.raises(ValidationError, match=message):
            ClassificationMethods(segment_thresholds=bad)

    @pytest.mark.parametrize(
        "good",
        [
            [0.5],                    # one segment: thresholds the overall rate
            [1.5, 1.2],               # above one exempts the segment
            [0.2, 0.2, 0.2],          # flat: no monotonicity requirement
            [0.01, 0.1, 0.3, 1.1],    # rising: a legal grid point
        ],
    )
    def test_accepted_lists(self, good):
        assert ClassificationMethods(segment_thresholds=good).segment_thresholds == good

    def test_a_list_that_differs_only_in_thresholds_is_not_equal_to_the_default(self):
        """The config layer forwards the block iff it differs from the default;
        the list has to take part in that comparison."""
        assert ClassificationMethods(segment_thresholds=[0.5, 0.5]) != ClassificationMethods()


class TestNeedsSegments:
    @pytest.mark.parametrize(
        "kwargs, expected",
        [
            ({}, True),
            ({"index": False, "time": True}, True),
            ({"time": True, "slope_time": True}, True),
            ({"index": False, "slope_index": True}, False),
            ({"index": False, "slope_index": True, "slope_time": True}, False),
        ],
    )
    def test_only_the_segment_methods_cut_segments(self, kwargs, expected):
        assert ClassificationMethods(**kwargs).needs_segments is expected


def test_round_trips_through_a_plain_dict():
    """to_state() and the config layer both move this model as a dict."""
    m = ClassificationMethods(
        index=False, time=True, segment_thresholds=[0.5, 0.2],
        slope_time=True, slope_threshold=-0.2, decision="majority",
    )
    assert ClassificationMethods(**m.model_dump()) == m
