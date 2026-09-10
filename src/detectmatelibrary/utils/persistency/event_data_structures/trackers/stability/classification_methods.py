"""Which stability classification methods run, and how they combine."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

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

    ``slope_threshold`` is shared by both slope methods: they are the same
    quantity measured on two axes and land on the same [-0.5, +0.5] scale,
    so one number keeps them comparable.
    """

    model_config = ConfigDict(extra="forbid")

    index: bool = True
    time: bool = False
    slope_index: bool = False
    slope_time: bool = False
    slope_threshold: float = -0.05
    decision: Literal["consensus", "majority"] = "consensus"

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
