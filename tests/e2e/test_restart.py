"""Chain C4: a detector trained on audit.log through process() is stopped
after training and restarted from its saved state; on the rest of audit.log
it must raise the same alerts as the uninterrupted run, i.e. its chain C3
golden file.

The state goes either through export_state(path) / import_state(path), or
through a `persist:` block that saves on exit and restores on construction
(auto_load). The restarted detector gets the config the first one ended with
(the configure phase wrote its events), with both phases off: a restored
detector does not know that it finished training, and would otherwise train
again on its first records (team question Q-F).
"""
import pytest

from detectmatelibrary import detectors
from detectmatelibrary.base_detectors import PersistConfig, TrackerDetector
from tests.support import golden as golden_files
from tests.support.audit import TRAIN_UNTIL

# about 1 s per case: two in the default run, the rest opt-in
DETECTORS = [
    "NewValueDetector",
    "EventSequenceDetector",
    *(pytest.param(name, marks=pytest.mark.slow) for name in (
        "CharsetDetector", "NewValueComboDetector", "ValueRangeDetector", "BigramFrequencyDetector",
        "NewEventDetector")),
]


def _trained(name: str, records: list, persist: PersistConfig | None = None) -> TrackerDetector:
    """The detector of the C3 golden file after its configure and training
    phases."""
    entry = golden_files.read(f"audit/{name}")["config"]
    detector = getattr(detectors, name)(name=name, config={"detectors": {name: entry}})
    if persist is not None:
        detector = type(detector)(name=name, config=detector.config.model_copy(update={"persist": persist}))
    for record in records[:TRAIN_UNTIL]:
        assert detector.process(record) is None
    return detector


def _restarted(detector: TrackerDetector, persist: PersistConfig | None = None) -> TrackerDetector:
    """A new detector with the first one's final config, phases off."""
    config = detector.config.model_copy(
        update={"data_use_configure": None, "data_use_training": None, "persist": persist})
    return type(detector)(name=detector.name, config=config)


def _alerts(detector: TrackerDetector, records: list) -> list[list[str]]:
    return [list(output["logIDs"]) for output in map(detector.process, records) if output is not None]


@pytest.mark.parametrize("name", DETECTORS)
def test_export_then_import_gives_the_golden_alerts(name, audit_logs):
    golden = golden_files.read(f"audit/{name}")
    records = audit_logs(golden["parser"])

    first = _trained(name, records)
    first.export_state("state")
    restarted = _restarted(first)
    restarted.import_state("state")

    assert _alerts(restarted, records[TRAIN_UNTIL:]) == golden["alerts"]


@pytest.mark.parametrize("name", DETECTORS)
def test_persist_then_auto_load_gives_the_golden_alerts(name, audit_logs):
    golden = golden_files.read(f"audit/{name}")
    records = audit_logs(golden["parser"])

    with _trained(name, records, persist=PersistConfig(path="state")) as first:
        pass  # leaving the block saves the state
    with _restarted(first, persist=PersistConfig(path="state", auto_load=True)) as restarted:
        assert _alerts(restarted, records[TRAIN_UNTIL:]) == golden["alerts"]
