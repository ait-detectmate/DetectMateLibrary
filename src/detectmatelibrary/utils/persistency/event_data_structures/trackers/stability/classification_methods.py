"""Which stability classification methods run, and how they combine."""

from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

METHOD_NAMES = ("index", "time", "slope_index", "slope_time")


class ClassificationMethods(BaseModel):
    """Selection of stability classification methods plus the decision rule.

    Four independent methods, two primitives over two axes::

        index        segment-mean thresholds   equal-count boundaries
        time         segment-mean thresholds   equal-duration boundaries
        slope_index  change centroid           index positions
        slope_time   change centroid           normalized timestamps

    Any subset may be enabled and any one may stand alone. The default --
    ``index`` alone under ``consensus`` -- is the historical behaviour.

    Each primitive has one shared threshold setting. ``segment_thresholds``
    is read by both segment methods: one upper bound on the mean change
    rate per segment, and the list's length is the segment count, so the
    same cuts are scored the same way whichever axis placed them.
    ``slope_threshold`` is shared by both slope methods: they are the same
    quantity measured on two axes and land on the same [-0.5, +0.5] scale,
    so one number keeps them comparable.
    """

    model_config = ConfigDict(extra="forbid")

    index: bool = True
    time: bool = False
    segment_thresholds: list[float] = Field(default_factory=lambda: [1.1, 0.3, 0.1, 0.01])
    slope_index: bool = False
    slope_time: bool = False
    slope_threshold: float = -0.05
    decision: Literal["consensus", "majority"] = "consensus"

    @field_validator("segment_thresholds")
    @classmethod
    def _positive_finite_thresholds(cls, value: list[float]) -> list[float]:
        """Non-empty, finite, strictly positive.

        No monotonicity: whether
        thresholds should tighten towards the end is an experiment choice,
        and a flat list is a legal grid point.
        """
        if not value:
            raise ValueError(
                "at least one segment threshold is required; "
                "the list's length is the segment count"
            )
        if not all(isfinite(t) for t in value):
            raise ValueError("segment thresholds must be finite")
        if any(t <= 0 for t in value):
            raise ValueError(
                "segment thresholds must be positive: a segment mean is never "
                "negative, so a threshold at or below zero can never pass"
            )
        return value

    @model_validator(mode="after")
    def _at_least_one_method(self) -> "ClassificationMethods":
        if not self.enabled:
            raise ValueError(
                "at least one classification method must be enabled "
                f"({', '.join(METHOD_NAMES)}). With none enabled, every variable "
                "that is not INSUFFICIENT_DATA, STATIC or RANDOM would be "
                "classified STABLE by default -- those three are decided before "
                "any method is consulted."
            )
        return self

    @property
    def enabled(self) -> tuple[str, ...]:
        """Enabled method names, in the order they appear in the config
        block."""
        return tuple(name for name in METHOD_NAMES if getattr(self, name))

    @property
    def needs_timestamps(self) -> bool:
        """Whether any enabled method reads the time axis.

        The tracker gates timestamp collection on this: with only index-axis
        methods enabled, recording stamps would cost memory nothing reads.
        """
        return self.time or self.slope_time

    @property
    def needs_segments(self) -> bool:
        """Whether any enabled method cuts the series into segments (index or
        time).

        The classifier's sample floor reads this: a slope-only block has
        no segments, so the threshold list it never consults must not
        gate its verdicts.
        """
        return self.index or self.time
