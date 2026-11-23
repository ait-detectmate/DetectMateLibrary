# flake8: noqa


# --8<-- [start:example_1]
from detectmatelibrary.utils import persistency

ep = persistency.EventPersistency()

ep.ingest_event(
    event_id="4624",
    event_template="An account was successfully logged on.",
    named_variables={"AccountName": "alice", "LogonType": "3"},
)

tracker = ep.get_event_data("4624")  # or ep["4624"]
# --8<-- [end:example_1]


# --8<-- [start:example_2]
from detectmatelibrary.utils import persistency

event_id = "1234"
event_template = "hello world"
variables = ["a", "b", "c"]
name_variables = {"Commander": "S."}

ep.ingest_event(
    event_id,
    event_template,
    variables=variables,
    named_variables=name_variables,
)

ep.get_event_data(event_id)        # backend for a single event
ep.get_events_data()               # dict[event_id -> backend]
ep.get_event_template(event_id)
ep.get_event_templates()
ep.get_events_seen()               # all event IDs ever ingested
ep[event_id]
# --8<-- [end:example_2]


# --8<-- [start:example_3]
from detectmatelibrary.utils import persistency

saver = persistency.PersistencySaver(
    ep,
    persistency.PersistencySaverConfig(
        path="./state/my-detector",
        save_interval_seconds=300,
        events_until_save=10_000,     # save after this many ingests, too
        auto_load=False,
        storage_options={},           # forwarded to fsspec
    ),
)
saver.start()
# ... detector runs ...
saver.stop()    # final flush, stops the background timer
# --8<-- [end:example_3]


# --8<-- [start:example_4]
from detectmatelibrary.utils import persistency

saver = persistency.PersistencySaver(
    ep,
    persistency.PersistencySaverConfig(path="./state/my-detector", auto_load=True),
)
# ep is now pre-populated from disk
# --8<-- [end:example_4]


# --8<-- [start:example_5]
from detectmatelibrary.utils import persistency

# Export to a file URI
persistency.save(ep, "./snapshots/trained-state")

# Export to bytes (no disk I/O; useful when sending state over a network API)
data: bytes = persistency.save(ep)

# Import from a file URI
persistency.load(ep, "./snapshots/trained-state")

# Import from bytes
persistency.load(ep, data)
# --8<-- [end:example_5]

# --8<-- [start:example_7]
from detectmatelibrary.bases.base_detectors import TrackerDetector, TrackerDetectorConfig

class MyDetectorConfig(TrackerDetectorConfig):
    method_type: str = "my_detector"

class MyDetector(TrackerDetector):
    def __init__(self, name="MyDetector", config=MyDetectorConfig()):
        super().__init__(name=name, config=config)

    def train(self, input_):
        self._ingest(input_, variables={...}, event_id=input_["eventID"])

    def detect(self, input_, output_):
        tracker = self.persistency.get_events_data().get(input_["eventID"])
        # compare against tracker to produce alerts
# --8<-- [end:example_7]

# --8<-- [start:example_6]
detector = MyDetector()

# Export to a file URI
detector.export_state("./snapshots/my-detector")

# Export to bytes (e.g. for an API response)
data: bytes = detector.export_state()

# Import from a file URI
detector.import_state("./snapshots/my-detector")

# Import from bytes (e.g. from an API request body)
detector.import_state(data)
# --8<-- [start:example_6]

import shutil
shutil.rmtree("./snapshots")
