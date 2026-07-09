# Persistency

The persistency module gives a detector a place to remember things about the
events it sees. State is keyed by `EventID` and survives across training, the
detection loop, and (optionally) restarts on disk.

This page is structured to read top-to-bottom: first the mental model, then a
quick start, then the API surface.

## Mental model

Persistency has three moving parts. Understanding what each one does makes the
rest of the page much easier to follow.

### 1. Events

Logs are grouped by `EventID`. Two events with the same ID share a template
but have their own variable values. Persistency stores **one independent state
object per event ID**, so an `EventStabilityTracker` for `EventID=4733` does
not interfere with one for `EventID=4624`.

### 2. Backends (`EventDataStructure`)

A backend is the thing that actually stores the per-event state. Persistency
owns the dict `{event_id: backend}`; the backend itself decides *how* data is
kept.

Two families ship today:

- **DataFrame backends** (`EventDataFrame`, `ChunkedEventDataFrame`) keeps the
  raw rows. Very storage heavy and *not recommended* for production-ready detectors.
- **Tracker backends** (`EventStabilityTracker`) keep only derived features
  (e.g. "this variable has been constant for the last 10k events") that are relevant for the detector. Use these
  when you only need a summary or a subset of the log's information, not the raw history — they cost a fraction of
  the memory.

All backends implement the same four-method contract: `add_data`, `get_data`,
`dump`, `load`. That contract is what `EventPersistency` and
`PersistencySaver` rely on — anything you add later only has to follow it.

### 3. Saver lifecycle (`PersistencySaver`)

`EventPersistency` itself is in-memory. To survive a process restart, the
state has to be written somewhere. `PersistencySaver` wraps an
`EventPersistency` and:

- writes to disk (or any `fsspec` URI) on two triggers — a wall-clock interval
  and an event-count threshold;
- optionally `auto_load`s previously saved state during construction;
- exposes `start()` / `stop()` so the background timer can be torn down
  cleanly. `stop()` is idempotent and is called automatically when a
  `Component` is used as a context manager.

In practice a detector never instantiates `PersistencySaver` directly: it sets
a `persist:` block in its config and `CoreDetector` wires the saver up via
`init_persistency`.

---

## Quick start

```python
from detectmatelibrary.utils import persistency

ep = persistency.EventPersistency(
    event_data_class=persistency.EventStabilityTracker,
)

ep.ingest_event(
    event_id="4624",
    event_template="An account was successfully logged on.",
    named_variables={"AccountName": "alice", "LogonType": "3"},
)

tracker = ep.get_event_data("4624")  # or ep["4624"]
```

That snippet covers the whole in-memory API: pick a backend class, ingest
events, query state.

---

## API reference

### `EventPersistency`

| Parameter | Description |
|---|---|
| `event_data_class` | An `EventDataStructure` subclass; one instance is created per event ID. |
| `variable_blacklist` | Variable names to skip when ingesting. Defaults to `["Content"]`. |
| `event_data_kwargs` | Extra kwargs forwarded to each backend instance. |

Common methods:

```python
ep.ingest_event(event_id, event_template, variables=..., named_variables=...)

ep.get_event_data(event_id)        # backend for a single event
ep.get_events_data()               # dict[event_id -> backend]
ep.get_event_template(event_id)
ep.get_event_templates()
ep.get_events_seen()               # all event IDs ever ingested
ep[event_id]                       # alias for get_event_data
```

### Available backends

| Class | Use when |
|---|---|
| `persistency.EventDataFrame` | You need history and a Pandas DataFrame is the natural shape. |
| `persistency.ChunkedEventDataFrame` | High-volume / streaming workloads — Polars-backed with row-retention and automatic compaction. |
| `persistency.EventStabilityTracker` | You only care about how variables behave over time (`STATIC` / `STABLE` / `UNSTABLE` / `RANDOM`). Cheapest memory footprint. |

All three are re-exported from the top of the package — `persistency.X` is the
canonical import; the deeply nested submodules are an implementation detail.

### Persisting to disk

```python
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
```

`PersistencySaver.save()` is thread-safe, and `stop()` is idempotent. The two
save triggers (`save_interval_seconds` and `events_until_save`) are
independent — whichever fires first wins.

#### Restoring state

```python
saver = persistency.PersistencySaver(
    ep,
    persistency.PersistencySaverConfig(path="./state/my-detector", auto_load=True),
)
# ep is now pre-populated from disk
```

If `auto_load=True` and no saved state exists, the constructor raises
`persistency.PersistencyLoadError` immediately — fail-fast rather than
silently starting empty.

#### Exporting and importing state on demand

For one-shot transfers — e.g. moving trained state to a new environment, or
taking a manual snapshot — use the standalone functions directly:

```python
from detectmatelibrary.utils import persistency

# Export to a file URI
persistency.save(ep, "./snapshots/trained-state")

# Export to bytes (no disk I/O — useful when sending state over a network API)
data: bytes = persistency.save(ep)

# Import from a file URI
persistency.load(ep, "./snapshots/trained-state")

# Import from bytes
persistency.load(ep, data)
```

`save` writes the same format as `PersistencySaver` and resets
`ep._events_since_save`. When called without a path it returns the state as a
zip archive in memory. `load` accepts either a path string or the bytes
returned by `save`; it raises `PersistencyLoadError` if no state exists at the
path, restores `event_data_class` and `event_data_kwargs` from metadata, and
clears any existing state in `ep` before loading.

Both functions are **not thread-safe** when called concurrently with a running
`PersistencySaver` on the same `ep`. Use the detector-level wrappers below
when a saver is active.

#### Detector-level export and import

When working through a detector (the typical path for DetectMateService), use
the methods on the detector object directly — no need to access
`EventPersistency` internals:

```python
# Export to a file URI
detector.export_state("./snapshots/my-detector")

# Export to bytes (e.g. for an API response)
data: bytes = detector.export_state()

# Import from a file URI
detector.import_state("./snapshots/my-detector")

# Import from bytes (e.g. from an API request body)
detector.import_state(data)
```

`import_state` is thread-safe: it acquires the saver lock before loading when
a `PersistencySaver` is running. Both methods raise `RuntimeError` if the
detector has no persistency configured.

### Storage backends (fsspec)

`PersistencySaverConfig.path` accepts any URI fsspec understands: a local path
(`./state`), `s3://bucket/key`, `gs://...`, `az://...`, and so on. Provider
credentials and tuning knobs go in `storage_options`.

---

## Using persistency inside a detector

The recommended path: declare `persist:` in the detector's config and let
`CoreDetector._register_persistency` build the saver for you. See
[Saving state (persist)](../detectors.md#saving-state-persist) for the config
schema.

In detector code, the pattern is:

```python
from detectmatelibrary.common.detector import CoreDetector
from detectmatelibrary.utils import persistency

class MyDetector(CoreDetector):
    def __init__(self, name="MyDetector", config=MyDetectorConfig()):
        super().__init__(name=name, config=config)
        self.persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker,
        )
        self._register_persistency(self.persistency)

    def train(self, input_):
        self.persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            named_variables={...},
        )

    def detect(self, input_, output_):
        tracker = self.persistency.get_events_data().get(input_["EventID"])
        # compare against tracker to produce alerts
```

`_register_persistency` is a one-line wrapper around
`init_persistency`; the helper
honours `config.persist` and returns `None` (so `self.saver` stays `None`)
when persistence is disabled.
