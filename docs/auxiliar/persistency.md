# Persistency

The persistency module provides event-based state management for detectors. It allows detectors to accumulate, store, and query data across their lifecycle — during training, detection, and auto-configuration.

## EventPersistency

`EventPersistency` is the main entry point. It manages one storage backend instance per event ID, so each event type maintains its own isolated state.

### Creating an instance

```python
from detectmatelibrary.common.persistency import EventPersistency

persistency = EventPersistency(
    event_data_class=MyBackend,          # storage backend class (see below)
    variable_blacklist=["Content"],      # variable names to exclude (optional)
    event_data_kwargs={"max_rows": 1000} # extra kwargs forwarded to the backend (optional)
)
```

| Parameter | Description |
|---|---|
| `event_data_class` | An `EventDataStructure` subclass that defines how data is stored and queried. |
| `variable_blacklist` | Variable names to exclude from storage. Defaults to `["Content"]`. |
| `event_data_kwargs` | A dictionary of keyword arguments forwarded to the backend constructor. |

### Storing data

```python
persistency.ingest_event(
    event_id=event_id,
    event_template=template,
    variables=positional_vars,        # optional positional variables
    named_variables=named_vars        # optional named variables
)
```

Each call appends data to the backend associated with the given `event_id`. If no backend exists for that ID yet, one is created automatically.

### Retrieving data

```python
# Single event
data = persistency.get_event_data(event_id)

# All events
all_data = persistency.get_events_data()  # dict[event_id -> backend]

# Templates
template = persistency.get_event_template(event_id)
all_templates = persistency.get_event_templates()

# Bracket access
backend = persistency[event_id]
```

## Storage backends

The backend determines how ingested data is stored and what queries are available. Choose the backend that fits your detector's needs.

### DataFrame backends

Store raw event data in tabular form. Useful when a detector needs to query or iterate over historical values.

- **`EventDataFrame`** — Pandas-backed storage. Simple and familiar.
- **`ChunkedEventDataFrame`** — Polars-backed storage with configurable row retention and automatic compaction. Suited for high-volume or streaming workloads.

```python
from detectmatelibrary.common.persistency.event_data_structures.dataframes import (
    EventDataFrame,
    ChunkedEventDataFrame,
)
```

### Tracker backends

Track variable behavior over time rather than storing raw data. Useful when a detector needs to understand how variables evolve (e.g., whether they converge to constant values). Is optimized for space efficiency since only extracted features from the logs are stored.

- **`EventStabilityTracker`** — Classifies each variable as `STATIC`, `STABLE`, `UNSTABLE`, `RANDOM`, or `INSUFFICIENT_DATA` based on how its values change over time.

```python
from detectmatelibrary.common.persistency.event_data_structures.trackers import (
    EventStabilityTracker,
)
```

## Usage in detectors

Persistency is **optional**. A detector can function without it. When a detector does need to maintain state across events — for example, to learn normal values during training and flag deviations during detection — it can integrate persistency by following this pattern:

### 1. Initialize in `__init__`

Create one or more `EventPersistency` instances with the appropriate backend.

```python
class MyDetector(CoreDetector):
    def __init__(self, name="MyDetector", config=MyDetectorConfig()):
        super().__init__(name=name, ...)
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
```

### 2. Accumulate state in `train()`

During training, ingest each event so the backend builds up its internal state.

```python
def train(self, input_):
    variables = self.get_configured_variables(input_, self.config.events)
    self.persistency.ingest_event(
        event_id=input_["EventID"],
        event_template=input_["template"],
        named_variables=variables,
    )
```

### 3. Query state in `detect()`

During detection, query the accumulated state to decide whether the incoming event is anomalous.

```python
def detect(self, input_, output_):
    for event_id, backend in self.persistency.get_events_data().items():
        stored_data = backend.get_data()
        # compare input_ against stored_data to produce alerts
```
