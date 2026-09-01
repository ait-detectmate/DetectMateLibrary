
# Components: Detectors

Detectors process structured logs from Parsers and emit alerts when anomalies are detected.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](schemas.md) | Structured log     |
| **Output** | [DetectorSchema](schemas.md)| Alert / finding    |

This document describes the minimal API, implementation guidance, a short example detector and a unit test pattern.

## CoreDetector — minimal API



```python
class CoreDetectorConfig(CoreConfig):
    component_type: str = "detectors"
    method_type: str = "core_detector"
    parser: str = "<PLACEHOLDER>"

    auto_config: bool = False


class CoreDetector(CoreComponent):
    def run(
        self, input_: List[ParserSchema] | ParserSchema, output_: DetectorSchema
    ) -> bool:
        """Define in the Core detector"""

    def detect(
        self,
        input_: List[ParserSchema] | ParserSchema,
        output_: DetectorSchema,
    ) -> bool:
        """Empty, must be define in the specific detector"""

    def train(
        self, input_: ParserSchema | list[ParserSchema]
    ) -> None:
        """Empty, can be define in the detector. It trains the detector"""
```

## Implementing a detector — example

Simple detector that raises an alert when a numeric variable exceeds a threshold.

```python
class SimpleThresholdConfig(CoreDetectorConfig):
    method_type: str = "simple_threshold"
    threshold: float = 0.0

class SimpleThresholdDetector(CoreDetector):
    def __init__(
        self, name: str = "SimpleThreshold",
        config: SimpleThresholdConfig | dict[str, Any] = SimpleThresholdConfig()
    ):

        if isinstance(config, dict):
            config = SimpleThresholdConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

    def detect(
        self,
        input_: schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:

        # calculate is a dummy method
        if calculate(input_) > self.config.threshold:

            output_["alertID"] = f"{self.name}-{int(time.time())}"
            output_["logIDs"].extend([ev.logID] if ev.logID else [])
            output_["score"] = float(value)
            output_["description"] = f"Value {value} > threshold {self.config.threshold}"
            return True

        return False
```
To configure the number of logs receive as input, you need to configure the [buffer](auxiliar/input_buffer.md) in the initialization of the Detector.

## Detectors methods

List of detectors:

* [Random detector](detectors/random_detector.md): Generates random alerts.
* [New Value](detectors/new_value.md): Detect new values in the variables in the logs.
* [Combo Detector](detectors/combo.md): Detect new combination of variables in the logs.
* [New Event](detectors/new_event.md): Detect new events in the variables in the logs.
* [Event Sequence](detectors/event_sequence.md): Detect unseen sequences of consecutive events in the logs.
* [Value Range](detectors/value_range.md) Detect numeric value ranges in variables in the logs.
* [Rule Based](detectors/rule_based.md): Detect anomalies based in a set of rules.
* [Bigram Frequency](detectors/bigram_frequency.md): Detect bigram-frequency-based anomalies in the logs.
* [Charset](detectors/charset.md): Detect new characters in the variables in the logs.
* [Deeplog](detectors/deeplog.md): Detect anomalies of a sequence of evend IDs with a LSTM.
* [LogBert](detectors/logbert.md): Detect anomalies of a sequence of evend IDs with a Transformer.
* [SCVS Detector](detectors/scvs_detector.md): Detect anomalies by looking at different sequence count vectors.
* [ECVC Detector](detectors/ecvc_detector.md): Detect anomalies by calculating the distance between different sequence count vectors.

## Configuration

When `auto_config` is set to `False`, the detector expects an explicit `events` or `global` block that specifies exactly which variables to monitor. `events`refers to event-specific variables while `global` refers to variables, that are not bound to events (`header_variables`can but don't have to be event bound):

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    auto_config: False
    data_use_configure: None  # Data used for configuration
    data_use_training: 199  # Data used for training
    params: {}  # global parameters
    events:  # event-specific configuration
      1:  # event_id
        instance1:  # name of instance (arbitrary)
          params: {}  # additional params
          variables:
            - pos: 0  # location of an unnamed variable from the log message
              name: var1  # name of variable (arbitrary)
          header_variables:
            - pos: level  # location of a named variable (defined in log_format of parser)
    global:  # define global instance for new_value_detector similar to "events"
      global_instance1:  # define instance name
        header_variables:  # same logic as header_variables in "events"
          - pos: Status
```


### Configuration semantics (preliminary)

**`events` key** — The integer key is the `EventID` (or `event_id`) to monitor (see the [Template Matcher](parsers/template_matcher.md) docs for how the EventID is assigned.

**`global` key** - This one has a similar functionality as the `events` key but refers to variables, that are not bound to events (thus can only contain `header_variables`).

**`variables[].pos`** — The 0-indexed position of the `<*>` wildcard in the matched template, counting from left to right starting at 0. For example, given:

```text
pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'
```

`pos: 0` captures `pid=`, `pos: 6` captures `exe=`, etc.

**`header_variables[].pos`** — A named field from the log format string (e.g., `Type`, `Time`, `Content`) rather than a wildcard position.


### Auto-configuration (optional)

Detectors can optionally support **auto-configuration** — a process where the detector automatically discovers which variables are worth monitoring, instead of requiring the user to specify them manually.

Auto-configuration is controlled by the `auto_config` flag in the pipeline config (e.g. `config/pipeline_config_default.yaml`):

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    auto_config: True       # enable auto-configuration
    params: {}
    # no "events" block needed — it will be generated automatically
```


### How it works

When auto-configuration is enabled, the detector goes through two extra phases before training:

**Phase 1 — `configure(input_)`**: The detector ingests events into an `EventPersistency` instance that uses a tracker backend to analyze variable behavior — for example, whether each variable is stable, random, or still has insufficient data. This instance is typically separate from the one used for training, because the configuration phase needs to observe *all* variables to decide which ones are worth monitoring, while training only tracks the variables that were selected as a result.

**Phase 2 — `set_configuration()`**: After enough data has been ingested, the detector queries the tracker to select variables that meet its criteria (e.g. only stable variables). It then generates a full `events` configuration from those results and updates its own config. At this point `auto_config` is set to `False` in the generated config, since the configuration is now explicit.

After these two phases, the detector proceeds with the normal `train()` and `detect()` lifecycle using the generated configuration.

### Implementation pattern

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

The `set_configuration()` method queries the tracker results and writes the
final `events` block. It touches nothing else on the config — everything the
operator set under `params` or `auto_config_params` must survive untouched, so
`set_configuration` never rebuilds the config from scratch:

```python
def set_configuration(self):
    variables = {}
    for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
        stable_vars = tracker.get_features_by_classification("STABLE")
        variables[event_id] = stable_vars

    self.config.events = generate_events_config(variables, self.name)
    self.config.auto_config = False
```

### Full lifecycle with auto-configuration

```python
1. configure(input_)         # call for each event in the dataset
2. set_configuration()       # finalize which variables to monitor
3. train(input_)             # call for each event in the dataset
4. detect(input_, output_)   # call for each event to detect anomalies
```

When `auto_config` is `False`, steps 1 and 2 are skipped entirely.

That distinction is visible in the config. A detector's settings live in two
blocks:

* **`auto_config_params`** — inputs *to* the configure phase. They pick which
  variables the phase selects and are read only while `auto_config` is `True`.
* **`params`** — operational settings, read during training and detection on
  every run.

The configure phase writes its results into the top-level `events` block (and,
for `EventSequenceDetector`, into `fixed_window_size`) and then sets
`auto_config` to `False`. It never modifies either input block, so a config can
be rerun with `auto_config: False` and reproduce the same detector.


### Stability classification (optional)

Stability classification decides whether a variable's change history counts as
`STABLE` by running one or more classification methods against it and combining
their verdicts. There are four independent methods, over two primitives and two
axes:

| method | what it thresholds | axis |
|---|---|---|
| `index` | segment-mean thresholds | equal-count boundaries |
| `time` | segment-mean thresholds | equal-duration boundaries |
| `slope_index` | change centroid vs. `slope_threshold` | index positions |
| `slope_time` | change centroid vs. `slope_threshold` | normalized timestamps |

Any subset of the four may be enabled, and any single one may stand alone. The
default — `index` alone — is the historical behaviour: each segment's mean rate
of change is compared against a threshold, and the segments are **equal-count**:
each holds the same number of observations, regardless of how much time they
cover. For bursty log sources that is misleading — a variable that changed
constantly during a quiet night and then went silent under a flood of daytime
traffic looks stable, because the flood supplies enough samples to dominate the
later segments. Enabling `time` cuts the same four segments at **equal
durations** instead, so each segment covers the same amount of wall-clock time;
the detector then needs an event time per record, which it reads from the log's
named variables (`logFormatVariables`, i.e. the fields declared in the parser's
`log_format`) under the name given by `timestamp_variable`. `slope_index` and
`slope_time` ask a different question — whether the change centroid sits early
or late in the series — on the index axis and the time axis respectively.

These parameters live on every `VariableDetector` subclass (`NewValueDetector`,
`NewValueComboDetector`, `ValueRangeDetector`, `CharsetDetector`, `BigramDetector`, …)
and go in the detector's `auto_config_params` block — they are inputs to the
auto-configuration phase, read only while `auto_config` is `True`, and never
consulted at detection time.

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    auto_config: True
    auto_config_params:
      use_stable_vars: True
      use_static_vars: True
      classification:
        index: True            # segment-mean thresholds, equal-count cuts
        time: False            # segment-mean thresholds, equal-duration cuts
        slope_index: False     # change centroid over index positions
        slope_time: False      # change centroid over normalized time
        slope_threshold: -0.05 # shared by both slope methods
        decision: consensus    # consensus | majority
      timestamp_variable: Time
      timestamp_format: "%y%m%d %H%M%S"
```

Defaults reproduce the historical behaviour exactly: `index: True`, the other
three `False`, `decision: consensus`, `slope_threshold: -0.05`. A config that
sets nothing under `classification` classifies identically to before this change.

#### The decision rule

When more than one method is enabled, `decision` picks how their verdicts
combine. `consensus` requires every enabled method to return stable; `majority`
requires strictly more than half of them to.

| enabled | `consensus` needs | `majority` needs | differ? |
|---|---|---|---|
| 1 | 1/1 | 1/1 | no |
| 2 | 2/2 | 2/2 (a 1–1 tie is UNSTABLE) | no |
| 3 | 3/3 | 2/3 | yes |
| 4 | 4/4 | 3/4 (a 2–2 tie is UNSTABLE) | yes |

Ties resolve to UNSTABLE. That keeps `majority` from ever being more lenient
than a coin-flip, and makes it collapse onto `consensus` at one and two enabled
methods — turning a third method on is the only place the rule starts to matter.

**All four methods false is a config error**, rejected by a pydantic validator.
It is not a harmless no-op: classification decides `INSUFFICIENT_DATA`,
`STATIC` and `RANDOM` before any method is consulted, so a method-less config
would silently classify every remaining variable `STABLE`.

#### Fields

All of these live in the detector's `auto_config_params` block.

| Field | Type | Default | Description |
|---|---|---|---|
| `use_stable_vars` | `bool` | `true` | Include variables classified `STABLE` in the generated configuration. |
| `use_static_vars` | `bool` | `true` | Include variables classified `STATIC`. Defaults to `false` on `NewValueComboDetector`. |
| `classification` | `ClassificationMethods` | see below | Which classification methods run and how their verdicts combine. |
| `timestamp_variable` | `str \| null` | `null` | Name of the field in `logFormatVariables` holding the record's event time. Required for `time` and `slope_time` to have any effect. Only named log-format fields are consulted — never the positional `variables` list. |
| `timestamp_format` | `str \| null` | `null` | Explicit [`strftime`](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes) pattern for parsing that field. When unset, `TimeFormatHandler` auto-detects the format (ISO 8601, Apache, syslog, numeric epoch seconds/milliseconds, and other common layouts). |

Set `timestamp_format` when the source uses a layout the auto-detection does not
know. The HDFS loghub corpus, for example, stamps records as `081109 203615`, which
only parses with an explicit `"%y%m%d %H%M%S"`.

`classification`'s six fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `index` | `bool` | `true` | Segment-mean thresholds, equal-count boundaries. |
| `time` | `bool` | `false` | Segment-mean thresholds, equal-duration boundaries. Needs `timestamp_variable`. |
| `slope_index` | `bool` | `false` | Change centroid vs. `slope_threshold`, measured on index positions. |
| `slope_time` | `bool` | `false` | Change centroid vs. `slope_threshold`, measured on normalized timestamps. Needs `timestamp_variable`. |
| `slope_threshold` | `float` | `-0.05` | The change-centroid cut-off both slope methods compare against, on a shared `[-0.5, +0.5]` scale. A variable passes when its centroid is at or below this value. |
| `decision` | `"consensus" \| "majority"` | `"consensus"` | How verdicts from more than one enabled method combine; see above. |

#### Fallback behaviour

Time-aware classification is best-effort and never fails a run:

* If `time` or `slope_time` is enabled but `timestamp_variable` is unset, or the named
  field is absent from a record, or its value cannot be parsed, the detector logs a
  **single** warning (once per detector, so a bad config cannot flood the log) and
  falls back to the index axis.
* If timestamps stop lining up with the recorded observations, or the observed time
  span is zero, or they arrive out of order, `time` silently reuses the equal-index
  cuts, and `slope_time` computes its centroid on the index axis instead — it
  degrades to `slope_index`.
* Under `majority`, a fallen-back method still casts its own vote: if `slope_index`
  and `slope_time` are both enabled and timestamps are unusable, both entries compute
  the same index-axis centroid, and that verdict carries two of the votes rather than
  one. This is deliberate — dropping a fallen-back method from the vote would change
  the enabled count from variable to variable and make `majority` mean something
  different for each one. The reason string names the axis each slope actually used,
  so a doubled vote is visible in the note.
* The same doubling applies to the segment-threshold pair: if `index` and `time` are
  both enabled and timestamps are unusable, `time` silently reuses the same equal-count
  cuts as `index`, so an identical verdict again carries two votes under `majority`
  rather than one. Unlike the slope pair, the reason string does not surface this —
  each entry is still labelled by its configured method name (`index` or `time`), not
  by the axis it actually used, so a doubled segment-pair vote is invisible in the note.

In every fallback case classification still runs and produces a result — only the
axis behind it changes back to index.

A segment with no observations in it is *not* a fallback: it scores a mean of 0.0,
because nothing observed means nothing changed. Equal-duration cuts of a bursty
variable leave such segments routinely, so `time` on its own is lenient towards a
burst of churn followed by silence. Enable `index` and `time` together when that
leniency matters — the index pass keeps every segment populated.


### Saving state (persist)

Detectors can persist their training state to disk (or cloud storage) so it
can be restored in a later session. Configure this with a top-level `persist:`
block in the detector config:

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    persist:
      path: ./state               # base path; detector name is appended automatically
      interval_seconds: 300       # save every N seconds (default: 300)
      events_until_save: null     # also save after N ingested events (default: disabled)
      auto_load: false            # restore saved state on startup (default: false)
      storage_options: {}         # backend credentials (see below)
    events:
      ...
```

All fields are optional — `persist: {}` uses all defaults. Omitting `persist:` entirely
disables saving (backward compatible).

The detector name is automatically appended to `path`, so `path: ./state` for a detector
named `NewValueDetector` writes to `./state/NewValueDetector/`.

#### Running under systemd

The default `path` is CWD-relative. systemd services usually run with CWD `/`,
so `./state` would resolve to `/state` (wrong location, needs root). To avoid
this, set `StateDirectory=` in your unit file — systemd creates `/var/lib/<dir>`
with the right ownership and exports `$STATE_DIRECTORY`, which the default `path`
reads automatically. No explicit `path:` needed:

```ini
[Service]
User=detectmate
StateDirectory=detectmate     # → state at /var/lib/detectmate/<detector>/
```

Setting `path:` explicitly (e.g. an `s3://` URL) always overrides `$STATE_DIRECTORY`.

#### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | `$STATE_DIRECTORY` or `"./state"` | Base directory or cloud URL. Detector name is appended. Defaults to systemd's `$STATE_DIRECTORY` if set, else `./state` (see note above). |
| `interval_seconds` | `int` | `300` | Background save interval in seconds. |
| `events_until_save` | `int \| null` | `null` | Save after this many ingested events. `null` disables event-count triggering. |
| `auto_load` | `bool` | `false` | Load saved state on construction. Raises `PersistencyLoadError` if no state exists. |
| `storage_options` | `dict` | `{}` | Credentials and options forwarded to [fsspec](https://filesystem-spec.readthedocs.io/). |

#### Storage options examples

**Local filesystem** — no `storage_options` needed:

```yaml
persist:
  path: ./state
```

**S3**:

```yaml
persist:
  path: s3://my-bucket/detector-state
  storage_options:
    key: AKIAIOSFODNN7EXAMPLE
    secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    region_name: eu-west-1
```

S3-compatible storage (MinIO, etc.):

```yaml
persist:
  path: s3://my-bucket/detector-state
  storage_options:
    endpoint_url: http://minio:9000
    key: minioadmin
    secret: minioadmin
```

**Azure Blob Storage**:

```yaml
persist:
  path: az://my-container/detector-state
  storage_options:
    account_name: mystorageaccount
    account_key: base64encodedkey==
```

**GCS**:

```yaml
persist:
  path: gs://my-bucket/detector-state
  storage_options:
    project: my-gcp-project
    token: /path/to/service-account.json
```

In practice, credentials are usually supplied via environment variables
(`AWS_ACCESS_KEY_ID`, etc.) or instance roles — in which case `storage_options`
stays empty or is omitted.

Go back [Index](index.md)
