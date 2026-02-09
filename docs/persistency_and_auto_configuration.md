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

### 4. Auto-configuration (optional)

Detectors can optionally support **auto-configuration** — a process where the detector automatically discovers which variables are worth monitoring, instead of requiring the user to specify them manually.

#### Enabling auto-configuration

Auto-configuration is controlled by the `auto_config` flag in the pipeline config (e.g. `config/pipeline_config_default.yaml`):

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    auto_config: True       # enable auto-configuration
    params: {}
    # no "events" block needed — it will be generated automatically
```

When `auto_config` is set to `False`, the detector expects an explicit `events` block that specifies exactly which variables to monitor:

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    auto_config: False
    params: {}
    events:
      1:
        instance1:
          params: {}
          variables:
            - pos: 0
              name: var1
          header_variables:
            - pos: level
```

#### How it works

When auto-configuration is enabled, the detector goes through two extra phases before training:

**Phase 1 — `configure(input_)`**: The detector ingests events into an `EventPersistency` instance that uses a tracker backend to analyze variable behavior — for example, whether each variable is stable, random, or still has insufficient data. This instance is typically separate from the one used for training, because the configuration phase needs to observe *all* variables to decide which ones are worth monitoring, while training only tracks the variables that were selected as a result.

**Phase 2 — `set_configuration()`**: After enough data has been ingested, the detector queries the tracker to select variables that meet its criteria (e.g. only stable variables). It then generates a full `events` configuration from those results and updates its own config. At this point `auto_config` is set to `False` in the generated config, since the configuration is now explicit.

After these two phases, the detector proceeds with the normal `train()` and `detect()` lifecycle using the generated configuration.

#### Implementation pattern

A detector that supports auto-configuration typically creates a separate `EventPersistency` instance for this purpose (but doesn't have to):

```python
class MyDetector(CoreDetector):
    def __init__(self, ...):
        super().__init__(...)

        # main persistency for training / detection
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
        # separate persistency for auto-configuration
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
```

The `configure()` method ingests all available variables (not just configured ones) so the tracker can assess each one:

```python
def configure(self, input_):
    self.auto_conf_persistency.ingest_event(
        event_id=input_["EventID"],
        event_template=input_["template"],
        variables=input_["variables"],
        named_variables=input_["logFormatVariables"],
    )
```

The `set_configuration()` method queries the tracker results and generates the final config:

```python
def set_configuration(self):
    variables = {}
    for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
        stable_vars = tracker.get_variables_by_classification("STABLE")
        variables[event_id] = stable_vars

    config_dict = generate_detector_config(
        variable_selection=variables,
        detector_name=self.name,
        method_type=self.config.method_type,
    )
    self.config = MyDetectorConfig.from_dict(config_dict, self.name)
```

#### Full lifecycle with auto-configuration

```
1. configure(input_)         — call for each event in the dataset
2. set_configuration()       — finalize which variables to monitor
3. train(input_)             — call for each event in the dataset
4. detect(input_, output_)   — call for each event to detect anomalies
```

When `auto_config` is `False`, steps 1 and 2 are skipped entirely.
