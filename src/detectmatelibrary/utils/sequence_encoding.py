"""Encode event sequences and count vectors as EventPersistency keys.

`EventPersistency` keys events by ID, so detectors whose model is a set of
sequences store each sequence as a string key in `events_seen` and get save,
load and auto-load for free. Shared here rather than in any one detector so
detectors never have to import from each other.
"""

from typing import List, Sequence

from detectmatelibrary import schemas
from detectmatelibrary.tools.logging import logger
from detectmatelibrary.utils.persistency import EventPersistency

_SEQUENCE_SEPARATOR = "\x1f"


def encode_sequence(sequence: Sequence[int]) -> str:
    """Encode a sequence of integers as a persistency key."""
    return _SEQUENCE_SEPARATOR.join(str(event_id) for event_id in sequence)


def decode_sequence(encoded: str) -> tuple[int, ...]:
    """Inverse of `encode_sequence`."""
    return tuple(int(event_id) for event_id in encoded.split(_SEQUENCE_SEPARATOR))


def build_count_vec(input_: List[schemas.ParserSchema]) -> tuple[int, ...]:
    """Count how often each EventID occurs in a window, indexed by EventID."""
    sequence, n = [0], 0
    for in_ in input_:
        event = in_["EventID"]
        if n < event:
            for _ in range(n, event):
                sequence.append(0)
            n = event
        sequence[event] += 1

    return tuple(sequence)


def encode_count_vec(window_size: int, count_vec: tuple[int, ...]) -> str:
    """Encode a count vector as a persistency key.

    The window size leads the key so restored state can be compared against the
    configured window: a count vector's length is max(EventID) + 1, which says
    nothing about the window it was counted over.
    """
    return encode_sequence((window_size, *count_vec))


def decode_count_vec(encoded: str) -> tuple[int, tuple[int, ...]]:
    """Inverse of `encode_count_vec`, as (window size, count vector)."""
    window_size, *count_vec = decode_sequence(encoded)
    return window_size, tuple(count_vec)


def warn_on_window_size_mismatch(
    name: str, event_persistency: EventPersistency, window_size: int
) -> None:
    """Warn when restored count vectors were trained at another window size.

    Count vectors are only comparable within the window they were
    counted over, so every restored vector would miss and detection
    would degrade into a stream of false positives.
    """
    restored = event_persistency.get_events_seen()
    if not restored:
        return
    trained, _ = decode_count_vec(str(next(iter(restored))))
    if trained != window_size:
        logger.warning(
            f"[{name}] restored state was trained with window_size {trained}, but "
            f"window_size is {window_size}. Count vectors from different windows "
            "are not comparable — expect false positives until retrained."
        )
