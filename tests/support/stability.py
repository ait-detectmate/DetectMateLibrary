"""Change series and timestamps shared by the stability classifier and tracker
tests."""
from detectmatelibrary.utils.persistency.data_structures.trackers import SingleStabilityTracker


def series(n: int, *change_ranges: range) -> list:
    """A change series of length n with index 0 True plus the given ranges."""
    out = [False] * n
    out[0] = True
    for r in change_ranges:
        for i in r:
            out[i] = True
    return out


def feed(tracker: SingleStabilityTracker, change_series) -> None:
    """Drive a tracker so its change_series matches: fresh value on each
    True, a repeat otherwise."""
    seen = 0
    for changed in change_series:
        if changed:
            seen += 1
        tracker.add_value(f"v{seen}")


# The flag only bites where the segment thresholds do not already imply an
# early centroid, and that gap opens up with series length. Over 400 samples
# the quarters are wide enough to hold 29 changes under threshold 0.3 and 9
# under 0.1, so a variable can pass every segment test with its changes still
# sitting *late*: quarter means [0.01, 0.29, 0.09, 0.0] -> STABLE, centroid
# +0.028 -> not declining.
LATE_BUT_PASSING = series(400, range(171, 200), range(291, 300))


# Same length, changes up front: STABLE under the segment thresholds and
# strongly declining (centroid -0.464), so the flag leaves it alone.
EARLY = series(400, range(1, 31))


# Segment-UNSTABLE (quarter 1 mean 0.51 > 0.3) but strongly declining. The
# flag is a conjunct, so it can never rescue this one.
DENSE_EARLY = series(400, range(1, 151))


DIVERGENT_TIMES = [0.0, 30.0, 60.0] + [90.0 + 0.001 * i for i in range(37)]


# Burst fixture: 20 fresh values, each immediately repeated once, inside 40 ms,
# then a single further repeat an hour later. Equal-duration quarters put all 40
# early occurrences in quarter 0 and leave quarters 1 and 2 with nothing in them,
# which scores them 0.0 -- so time mode calls this churning variable STABLE and
# only count mode (or `both`) catches it.
BURSTY_VALUES = [f"v{i // 2}" for i in range(40)] + ["v19"]


BURSTY_TIMES = [0.001 * i for i in range(40)] + [3600.0]


def feed_divergent(tracker: SingleStabilityTracker) -> None:
    """3 new values spread over ~80s, then a repeated value bursting at
    t~100."""
    values = ["a", "b", "c"] + ["c"] * 37
    for value, ts in zip(values, DIVERGENT_TIMES):
        tracker.add_value(value, timestamp=ts)
