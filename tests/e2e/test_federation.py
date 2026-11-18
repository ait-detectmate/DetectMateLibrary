"""Chain C5: federated training on audit.log. Three client nodes, sharing
one configuration, each train on a third of the training lines; a server
node that saw no training data aggregates them. The server must then raise
the alerts of the detector's chain C3 golden file, as one node trained on
all of it does. On its own the server raises none of them, or hundreds of
false ones.

The clients join the server either with `+` or as to_binary() bytes, as
nodes on other machines would. Any one client alone would already pass on
this repetitive log, which is why the server gets no data of its own.
BigramFrequencyDetector is left out: its federation is disabled (team
question Q-E).
"""
import pytest

from detectmatelibrary import detectors
from detectmatelibrary.base_detectors import TrackerDetector
from detectmatelibrary.common.detector import CoreDetectorConfig
from tests.support import golden as golden_files
from tests.support.audit import TRAIN_UNTIL

# a few seconds per case: two in the default run, the rest opt-in
DETECTORS = [
    "NewValueDetector",
    "EventSequenceDetector",
    *(pytest.param(name, marks=pytest.mark.slow) for name in (
        "CharsetDetector", "NewValueComboDetector", "ValueRangeDetector", "NewEventDetector")),
]


def _configured(name: str, records: list) -> CoreDetectorConfig:
    """The config the C3 detector's configure phase produces, for all nodes."""
    entry = {**golden_files.read(f"audit/{name}")["config"], "data_use_training": None,
             "use_config_data_as_training": False}
    detector = getattr(detectors, name)(name=name, config={"detectors": {name: entry}})
    for record in records[:TRAIN_UNTIL]:  # the configure phase ends on the last one
        detector.process(record)
    assert detector.config.auto_config is False
    return detector.config.model_copy(update={"data_use_configure": None, "allow_fed": True})


def _client(name: str, config: CoreDetectorConfig, shard: list) -> TrackerDetector:
    config = config.model_copy(update={"data_use_training": len(shard)})
    client = getattr(detectors, name)(name=name, config=config)
    for record in shard:
        assert client.process(record) is None
    return client


@pytest.mark.parametrize("join", ["add", "stack_binary"])
@pytest.mark.parametrize("name", DETECTORS)
def test_server_of_three_clients_raises_the_golden_alerts(name, join, audit_logs):
    golden = golden_files.read(f"audit/{name}")
    records = audit_logs(golden["parser"])
    config = _configured(name, records)
    third = TRAIN_UNTIL // 3
    clients = [_client(name, config, records[start:start + third]) for start in (0, third, 2 * third)]
    server = getattr(detectors, name)(name=name, config=config)

    if join == "add":
        (server + clients[0] + clients[1] + clients[2]).aggregate()
    else:
        server.stack([client.to_binary() for client in clients])
        server.aggregate()

    outputs = map(server.process, records[TRAIN_UNTIL:])
    assert [list(output["logIDs"]) for output in outputs if output is not None] == golden["alerts"]


def _learned(detector: TrackerDetector) -> dict:
    """What each event's tracker learned, serialized (store equality ignores
    it: bug B11)."""
    return {event: tracker.dump() for event, tracker in detector.persistency.get_events_data().items()}


@pytest.mark.slow
@pytest.mark.parametrize("join", ["from_binary", "add"])
@pytest.mark.parametrize("name", ["ECVCDetector", "SCVSDetector"])
def test_count_vector_state_reaches_the_other_node(name, join, audit_logs):
    """ECVC and SCVS need post_train(), which an untrained server never runs,
    so for them the check is on the state: a copy (from_binary) or an
    untrained peer (aggregate) of a detector trained on audit.log holds its
    store, and for ECVC the count vectors and threshold built from it."""
    golden = golden_files.read(f"audit/{name}")
    config = {"detectors": {name: {**golden["config"], "allow_fed": True}}}
    trained = getattr(detectors, name)(name=name, config=config)
    for record in audit_logs(golden["parser"]):
        trained.process(record)
    other = getattr(detectors, name)(name=name, config=config)

    if join == "from_binary":
        other = other.from_binary(trained.to_binary())
    else:
        (trained + other).aggregate()

    assert trained.persistency.get_events_seen()
    assert _learned(other) == _learned(trained)
    if name == "ECVCDetector":
        assert (other.count_vecs == trained.count_vecs).all()
        assert other.threshold == trained.threshold
