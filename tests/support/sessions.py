"""A small synthetic HDFS-style log whose sessions (blocks) interleave, for the
session-window e2e chain (tests/e2e/test_sessions.py).

Every line is "<block> <message>". A normal block is opened, written
once or twice, closed and verified. The first TRAIN_SESSIONS blocks are
the training part; among the DETECT_SESSIONS blocks after them, the
ANOMALOUS ones break the pattern in three ways. The lines of the blocks
of one part interleave in a fixed pseudo-random order.

`python -m tests.support.sessions` rewrites the files in
tests/test_data/sessions/; a test checks that the committed log is what
generate() returns, so the two cannot drift apart.
"""
import random

from tests.support.paths import TEST_DATA

SESSIONS_DIR = TEST_DATA / "sessions"
SESSIONS_LOG = str(SESSIONS_DIR / "sessions.log")
SESSIONS_TEMPLATES = str(SESSIONS_DIR / "templates.txt")
LOG_FORMAT = "<blk> <Content>"

OPEN = "Receiving block {blk} src: /10.0.0.{n}:50010 dest: /10.0.0.{m}:50010"
WRITE = "Received block {blk} of size {size} from /10.0.0.{n}"
CLOSE = "PacketResponder {n} for block {blk} terminating"
VERIFY = "Verification succeeded for {blk}"
DELETE = "Deleting block {blk} file /data/{blk}"
TEMPLATES = [
    "Receiving block <*> src: <*> dest: <*>",
    "Received block <*> of size <*> from <*>",
    "PacketResponder <*> for block <*> terminating",
    "Verification succeeded for <*>",
    "Deleting block <*> file <*>",
]

TRAIN_SESSIONS = 40
DETECT_SESSIONS = 10
ANOMALOUS = {
    "blk_42": [OPEN, CLOSE, WRITE, VERIFY],  # written after closing
    "blk_45": [OPEN, WRITE, DELETE, CLOSE, VERIFY],  # an event never seen in training
    "blk_48": [WRITE, WRITE, CLOSE, VERIFY],  # never opened
}


def _session(blk: str, number: int, rng: random.Random) -> list[str]:
    steps = ANOMALOUS.get(blk) or [OPEN, WRITE, *([WRITE] if number % 3 else []), CLOSE, VERIFY]
    return [f"{blk} " + step.format(blk=blk, n=rng.randrange(1, 9), m=rng.randrange(1, 9),
                                    size=rng.randrange(1_000, 70_000)) for step in steps]


def _interleaved(sessions: list[list[str]], rng: random.Random) -> list[str]:
    """The sessions' lines in a random order that keeps each session's own
    order."""
    queues = [list(session) for session in sessions]
    lines = []
    while any(queues):
        queue = rng.choice([queue for queue in queues if queue])
        lines.append(queue.pop(0))
    return lines


def generate() -> str:
    rng = random.Random(0)
    parts = (range(TRAIN_SESSIONS), range(TRAIN_SESSIONS, TRAIN_SESSIONS + DETECT_SESSIONS))
    lines = []
    for part in parts:
        lines += _interleaved([_session(f"blk_{number}", number, rng) for number in part], rng)
    return "\n".join(lines) + "\n"


def training_lines() -> int:
    """How many lines the training part has."""
    rng = random.Random(0)
    return sum(len(_session(f"blk_{number}", number, rng)) for number in range(TRAIN_SESSIONS))


if __name__ == "__main__":
    SESSIONS_DIR.mkdir(exist_ok=True)
    (SESSIONS_DIR / "sessions.log").write_text(generate())
    (SESSIONS_DIR / "templates.txt").write_text("\n".join(TEMPLATES) + "\n")
