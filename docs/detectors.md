
# Detectors

Detectors process structured logs from Parsers and emit alerts when anomalies are detected.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](schemas.md) | Structured log     |
| **Output** | [DetectorSchema](schemas.md)| Alert / finding    |

This document describes the minimal API, implementation guidance, a short example detector and a unit test pattern.

## CoreDetector  --  minimal API



```python
class CoreDetectorConfig(CoreConfig):
    component_type: str = "detectors"
    method_type: str = "core_detector"
    parser: str = "PARSER"

    auto_config: bool = True
    events: EventsConfig | dict[str, Any] = {}
    global_instances: dict[str, Any] = {}  # written as `global` in YAML


class CoreDetector(CoreComponent):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: BufferMode = BufferMode.NO_BUF,
        buffer_size: int | None = None,
        config: CoreDetectorConfig | dict[str, Any] | None = CoreDetectorConfig(),
    ) -> None:
        """buffer_mode and buffer_size set how many logs detect() receives per call."""

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

    def train(self, input_: ParserSchema | list[ParserSchema]) -> None:
        """Empty, can be define in the detector. It trains the detector"""
```

## Implementing a detector  --  example

Simple detector that raises an alert when a numeric variable exceeds a threshold.

```python
class SimpleThresholdConfig(CoreDetectorConfig):
    method_type: str = "simple_threshold"
    threshold: float = 0.0


class SimpleThresholdDetector(CoreDetector):
    def __init__(
        self,
        name: str = "SimpleThreshold",
        config: SimpleThresholdConfig | dict[str, Any] = SimpleThresholdConfig(),
    ):

        if isinstance(config, dict):
            config = SimpleThresholdConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

    def detect(
        self, input_: schemas.ParserSchema, output_: schemas.DetectorSchema
    ) -> bool:

        # calculate is a dummy method
        if calculate(input_) > self.config.threshold:
            output_["alertID"] = f"{self.name}-{int(time.time())}"
            output_["logIDs"].extend([ev.logID] if ev.logID else [])
            output_["score"] = float(value)
            output_["description"] = (
                f"Value {value} > threshold {self.config.threshold}"
            )
            return True

        return False
```
To configure the number of logs receive as input, you need to configure the [buffer](auxiliar/input_buffer.md) in the initialization of the Detector.

## Detectors methods

The detectors are numbered from simplest to most complex, and the sidebar lists them in the same order. The simplest ones need no training or learn a plain set of values; the most complex are neural networks that need a lot of training data. If you are new to DetectMate, start at the top.

| # | Detector | What it detects |
|---|---|---|
| 00 | [Random Detector](detectors/random_detector.md) | Raises random alerts, for testing a pipeline. No training. |
| 01 | [Rule Detector](detectors/rule_based.md) | Logs that match fixed rules (unknown template, keyword, exception, error level). No training. |
| 02 | [New Event Detector](detectors/new_event.md) | Event IDs (log templates) never seen in training. |
| 03 | [New Value Detector](detectors/new_value.md) | Values of a variable never seen in training. |
| 04 | [New Value Combo Detector](detectors/combo.md) | Combinations of values never seen together in training. |
| 05 | [Value Range Detector](detectors/value_range.md) | Numeric values outside the range seen in training. |
| 06 | [Charset Detector](detectors/charset.md) | Characters in a variable never seen in training. |
| 07 | [Event Sequence Detector](detectors/event_sequence.md) | Orders of consecutive event IDs never seen in training. |
| 08 | [Bigram Frequency Detector](detectors/bigram_frequency.md) | Values whose character pairs are improbable under a learned frequency model. |
| 09 | [SCVS Detector](detectors/scvs_detector.md) | Sequence Count Vector Set: windows whose event counts never occurred in training. |
| 10 | [ECVC Detector](detectors/ecvc_detector.md) | Event Count Vector Clustering: windows whose event counts are far from those seen in training. |
| 11 | [DeepLog Detector](detectors/deeplog.md) | Unexpected next events in a sequence, predicted by an LSTM. |
| 12 | [LogBERT Detector](detectors/logbert.md) | Unexpected events in a sequence, predicted by a Transformer. |

## Configuration

!!! warning "Tell the detector how much data to learn from"
    `data_use_training` (logs used for training) and `data_use_configure` (logs used for
    auto-configuration) both default to `null`, which skips that phase. Without
    `data_use_training` a detector starts detecting with nothing learned; with
    `auto_config: true` but no `data_use_configure`, it never picks anything to monitor.
    Write `null`, not `None`, in YAML: `None` is read as a string.

!!! note "Long configure phases spill to disk"
    With `use_config_data_as_training: true` (the default) every log of the configure phase
    is kept until training starts, then replayed into training. Up to
    `train_buffer_max_records` logs (default 100000) stay in memory; beyond that the buffer
    is written as Parquet files to a private `detectmate-train-*` directory under
    `train_buffer_dir` (a local path; default: the system temp directory, or `TMPDIR`) and
    read back when training starts. A warning in the log marks the first spill. The
    directory is removed once training has read it; a process that is killed leaves it
    behind, and you can delete it by hand. To keep it off disk, lower `data_use_configure`
    or set `use_config_data_as_training: false`. In a container, the default directory is
    in the container's writable layer: point `train_buffer_dir` at a mounted volume when
    the configure phase is large. Where `/tmp` is a RAM-backed tmpfs (common on Fedora,
    Arch and Debian 13) the default spill uses RAM, so point `train_buffer_dir` at real
    disk. NewValueComboDetector reads its configure logs a second time, to learn which
    combinations are stable, so it keeps a copy of its own, which spills the same way.

Every detector page shows a minimal, working configuration file next to its example. The
reference below explains the blocks those files use.

When `auto_config` is set to `False`, the detector expects an explicit `events` or `global` block that specifies exactly which variables to monitor. `events` refers to event-specific variables while `global` refers to variables, that are not bound to events (`header_variables` can but don't have to be event bound):

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    auto_config: False
    params:  # detector-wide parameters
      data_use_training: 1000  # the first 1000 logs train the detector
    events:  # event-specific configuration
      1:  # event_id
        instance1:  # name of instance (arbitrary)
          params: {}  # additional params
          variables:
            - pos: 0  # location of an unnamed variable from the log message
              name: var1  # name of variable (arbitrary)
          header_variables:
            - pos: Level  # name of a field in the parser's log_format (case-sensitive: <Level> -> Level)
    global:  # define global instance for new_value_detector similar to "events"
      global_instance1:  # define instance name
        header_variables:  # same logic as header_variables in "events"
          - pos: Status
```


### Common parameters (all detectors)

There are some parameters, that **every** detector inherits from `CoreDetectorConfig`/`CoreConfig`/`BasicConfig`, regardless of what it does. The other parameters, that are **specific** for the respective detector, are explained right at the detectors documentation page, later on.

<!-- Start common_arguments -->
???+ note "Top level"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `auto_config` | boolean | True | Runs the configuration step before the training process. |
    | `events` | object | {} | Events configuration dict keyed by event_id. |
    | `global` | object | {} | Instances monitoring event-independent header variables (e.g. hostname, level), keyed by instance name. Written as `global` in YAML. |

???+ note "params"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `start_id` | integer | 10 | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `parser` | string | PARSER | Name of the parser used. |
<!-- End common_arguments -->

Beyond the common parameters, detectors inherit the parameters of the group they belong to.

### Tracker detectors

The detectors that keep their model in persistency stores ([New Event](detectors/new_event.md), [New Value](detectors/new_value.md), [New Value Combo](detectors/combo.md), [Value Range](detectors/value_range.md), [Charset](detectors/charset.md), [Event Sequence](detectors/event_sequence.md), [Bigram Frequency](detectors/bigram_frequency.md), [SCVS](detectors/scvs_detector.md), [ECVC](detectors/ecvc_detector.md)) share the following parameters, inherited from `TrackerDetectorConfig`. Only these detectors accept a `persist:` block (see [Saving state (persist)](#saving-state-persist)).

<!-- Start tracker_arguments -->
???+ note "Top level"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `persist` | object, null | None | Periodic state saving (path, interval_seconds, events_until_save, auto_load, storage_options). None disables it. See the Persistency page. |

???+ note "params"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `allow_fed` | boolean | False | Allow to do the federation |
<!-- End tracker_arguments -->

### Per-variable model detectors

The tracker detectors that learn a per-variable model ([Bigram Frequency](detectors/bigram_frequency.md), [Charset](detectors/charset.md), [New Value Combo](detectors/combo.md), [New Value](detectors/new_value.md), [Value Range](detectors/value_range.md)) also share the following parameters, inherited from `VariableDetectorConfig`.

<!-- Start variable_arguments -->
??? note "auto_config_params (read only while auto_config is true)"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `classification.index` | boolean | True | Segment-mean test over equal-count segments. |
    | `classification.time` | boolean | False | Segment-mean test over equal-duration segments. Needs timestamp_variable. |
    | `classification.segment_thresholds` | array | [1.1, 0.3, 0.1, 0.01] | Upper bound on the mean change rate, one per segment; the list length is the segment count. Used by index and time. |
    | `classification.slope_index` | boolean | False | Change-centroid test on the index axis. |
    | `classification.slope_time` | boolean | False | Change-centroid test on the time axis. Needs timestamp_variable. |
    | `classification.slope_threshold` | number | -0.05 | A variable is STABLE when its change centroid (-0.5 to +0.5) is at or below this. Used by slope_index and slope_time. |
    | `classification.decision` | string | consensus | How the enabled methods' verdicts combine: consensus needs all of them, majority needs more than half. |
    | `timestamp_variable` | string, null | None | Header variable (from the parser's log_format) holding each event's time. Required by the time and slope_time classification methods. |
    | `timestamp_format` | string, null | None | Format of timestamp_variable. None detects it automatically. |
    | `use_stable_vars` | boolean | True | Monitor the variables the configure phase classifies as STABLE. |
    | `use_static_vars` | boolean | True | Monitor the variables the configure phase classifies as STATIC (a single value). |
<!-- End variable_arguments -->

### Deep learning detectors

The two neural detectors ([DeepLog](detectors/deeplog.md), [LogBERT](detectors/logbert.md)) share the following parameters, inherited from `DeepLearningDetectorConfig`.

<!-- Start deeplearning_arguments -->
???+ note "params"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `window_size` | integer | 10 | Number of consecutive events used as one training/detection sequence. |
    | `validation_per` | number | 0.2 | Fraction of data held out for validation during (fine)training. |
    | `finetune_epochs` | integer | 2 | Number of epochs used when finetuning during the configuration phase. |
    | `hyperparameters` | object | {'Model': {}, 'Train': {}, 'Finetune': []} | Model, training and hyperparameter-search settings passed to the underlying deep learning model. |
<!-- End deeplearning_arguments -->

### Configuration semantics (preliminary)

**`events` key**  --  The integer key is the `EventID` (or `event_id`) to monitor (see the [Template Matcher](parsers/template_matcher.md) docs for how the EventID is assigned.

**`global` key** - This one has a similar functionality as the `events` key but refers to variables, that are not bound to events (thus can only contain `header_variables`).

**`variables[].pos`**  --  The 0-indexed position of the `<*>` wildcard in the matched template, counting from left to right starting at 0. For example, given:

```text
pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'
```

`pos: 0` captures the value after `pid=` (for example `10125`), `pos: 6` the value after
`exe=` (for example `"/usr/sbin/cron"`), and so on.

**`header_variables[].pos`**  --  A named field from the log format string (e.g., `Type`, `Time`, `Content`) rather than a wildcard position.


### Auto-configuration (optional)

Detectors can optionally support **auto-configuration**  --  a process where the detector automatically discovers which variables are worth monitoring, instead of requiring the user to specify them manually.

Auto-configuration is controlled by the `auto_config` flag in the pipeline config (e.g. `config/pipeline_config_default.yaml`):

```yaml
detectors:
  NewValueDetector:
    method_type: new_value_detector
    auto_config: True           # enable auto-configuration
    params:
      data_use_configure: 1000  # logs used to pick the variables
      data_use_training: 1000   # logs used to train on them afterwards
    # no "events" block needed  --  it will be generated automatically
```


### How it works

When auto-configuration is enabled, the detector goes through two extra phases before training:

**Phase 1  --  `configure(input_)`**: The detector ingests events into an `EventPersistency` instance that uses a tracker backend to analyze variable behavior  --  for example, whether each variable is stable, random, or still has insufficient data. This instance is typically separate from the one used for training, because the configuration phase needs to observe *all* variables to decide which ones are worth monitoring, while training only tracks the variables that were selected as a result.

**Phase 2  --  `set_configuration()`**: After enough data has been ingested, the detector queries the tracker to select variables that meet its criteria (e.g. only stable variables). It then generates a full `events` configuration from those results and updates its own config. At this point `auto_config` is set to `False` in the generated config, since the configuration is now explicit.

After these two phases, the detector proceeds with the normal `train()` and `detect()` lifecycle using the generated configuration.

To support auto-configuration in your own detector, see [Development](development.md#implement-auto-configuration-in-a-detector).

### Full lifecycle with auto-configuration

```python
1. configure(input_)         # call for each event in the dataset
2. set_configuration()       # finalize which variables to monitor
3. train(input_)             # call for each event in the dataset
4. detect(input_, output_)   # call for each event to detect anomalies
```

When `auto_config` is `False`, steps 1 and 2 are skipped entirely. `data_use_configure`
still reserves its records, and with `use_config_data_as_training` they still go to
training, so a config rerun with `auto_config: False` trains on exactly the data the
configuring run saw. This holds for every component with a configure phase, including
the hyperparameter searches of `DrainParser` and the deep-learning detectors.

That distinction is visible in the config. A detector's settings live in two
blocks:

* **`auto_config_params`**  --  inputs *to* the configure phase. They pick which
  variables the phase selects and are read only while `auto_config` is `True`.
* **`params`**  --  operational settings, read during training and detection on
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
default  --  `index` alone  --  is the historical behaviour: each segment's mean rate
of change is compared against its entry in `segment_thresholds`  --  four segments
by default, one threshold per segment  --  and the segments are **equal-count**:
each holds the same number of observations, regardless of how much time they
cover. For bursty log sources that is misleading  --  a variable that changed
constantly during a quiet night and then went silent under a flood of daytime
traffic looks stable, because the flood supplies enough samples to dominate the
later segments. Enabling `time` cuts the same segments at **equal
durations** instead, so each segment covers the same amount of wall-clock time;
the detector then needs an event time per record, which it reads from the log's
named variables (`logFormatVariables`, i.e. the fields declared in the parser's
`log_format`) under the name given by `timestamp_variable`. `slope_index` and
`slope_time` ask a different question  --  whether the change centroid sits early
or late in the series  --  on the index axis and the time axis respectively.

These parameters live on every `VariableDetector` subclass (`NewValueDetector`,
`NewValueComboDetector`, `ValueRangeDetector`, `CharsetDetector`, `BigramDetector`, …)
and go in the detector's `auto_config_params` block  --  they are inputs to the
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
        segment_thresholds: [1.1, 0.3, 0.1, 0.01]  # one per segment; the length is the segment count
        slope_index: False     # change centroid over index positions
        slope_time: False      # change centroid over normalized time
        slope_threshold: -0.05 # shared by both slope methods
        decision: consensus    # consensus | majority
      timestamp_variable: Time
      timestamp_format: "%y%m%d %H%M%S"
```

Defaults reproduce the historical behaviour exactly: `index: True`, the other
three `False`, `segment_thresholds: [1.1, 0.3, 0.1, 0.01]`, `decision: consensus`,
`slope_threshold: -0.05`. A config that sets nothing under `classification`
classifies identically to before these changes on every series with at least
four observations; the one exception is the segment floor described under
"Fields" below.

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
methods  --  turning a third method on is the only place the rule starts to matter.

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
| `timestamp_variable` | `str \| null` | `null` | Name of the field in `logFormatVariables` holding the record's event time. Required for `time` and `slope_time` to have any effect. Only named log-format fields are consulted  --  never the positional `variables` list. |
| `timestamp_format` | `str \| null` | `null` | Explicit [`strftime`](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes) pattern for parsing that field. When unset, `TimeFormatHandler` auto-detects the format (ISO 8601, Apache, syslog, numeric epoch seconds/milliseconds, and other common layouts). |

Set `timestamp_format` when the source uses a layout the auto-detection does not
know. The HDFS loghub corpus, for example, stamps records as `081109 203615`, which
only parses with an explicit `"%y%m%d %H%M%S"`.

`classification`'s seven fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `index` | `bool` | `true` | Segment-mean thresholds, equal-count boundaries. |
| `time` | `bool` | `false` | Segment-mean thresholds, equal-duration boundaries. Needs `timestamp_variable`. |
| `segment_thresholds` | `list[float]` | `[1.1, 0.3, 0.1, 0.01]` | Per-segment upper bounds on the mean change rate for `index` and `time`. The list's length is the segment count. Entries must be positive and finite and the list must not be empty; an entry above one exempts its segment. |
| `slope_index` | `bool` | `false` | Change centroid vs. `slope_threshold`, measured on index positions. |
| `slope_time` | `bool` | `false` | Change centroid vs. `slope_threshold`, measured on normalized timestamps. Needs `timestamp_variable`. |
| `slope_threshold` | `float` | `-0.05` | The change-centroid cut-off both slope methods compare against, on a shared `[-0.5, +0.5]` scale. A variable passes when its centroid is at or below this value. |
| `decision` | `"consensus" \| "majority"` | `"consensus"` | How verdicts from more than one enabled method combine; see above. |

The segment methods need at least one observation per segment. A variable with
fewer observations than segments is classified `INSUFFICIENT_DATA` (with a reason
naming the segment count) rather than scored over empty segments. The tracker's
own `min_samples` stays the floor for `STATIC` and `RANDOM`, which are decided
before any segment is cut; the effective minimum for a `STABLE` / `UNSTABLE`
verdict is the larger of the two. A block with only slope methods enabled cuts no
segments and has no such floor.

#### Fallback behaviour

Time-aware classification is best-effort and never fails a run:

* If `time` or `slope_time` is enabled but `timestamp_variable` is unset, or the named
  field is absent from a record, or its value cannot be parsed, the detector logs a
  **single** warning (once per detector, so a bad config cannot flood the log) and
  falls back to the index axis.
* If timestamps stop lining up with the recorded observations, or the observed time
  span is zero, or they arrive out of order, `time` silently reuses the equal-index
  cuts, and `slope_time` computes its centroid on the index axis instead  --  it
  degrades to `slope_index`.
* Under `majority`, a method that fell back still casts its own vote. If both methods
  of a pair (`slope_index`/`slope_time` or `index`/`time`) are enabled and timestamps
  are unusable, they compute the same verdict, which then counts twice.

In every fallback case classification still runs and produces a result  --  only the
axis behind it changes back to index.

A segment with no observations in it is *not* a fallback: it scores a mean of 0.0,
because nothing observed means nothing changed. Once the segment floor above is
met, equal-index cuts never leave a segment empty; equal-duration cuts of a bursty
variable still do, routinely, so `time` on its own is lenient towards a burst of
churn followed by silence. Enable `index` and `time` together when that leniency
matters  --  the index pass keeps every segment populated.


### Saving state (persist)

[Tracker detectors](#tracker-detectors) can persist their training state to disk
(or cloud storage) so it can be restored in a later session. Configure this with a
top-level `persist:` block in the detector config:

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

All fields are optional  --  `persist: {}` uses all defaults. Omitting `persist:` entirely
disables saving (backward compatible). The other detectors (Random, Rule, DeepLog,
LogBERT) have no state to save: a `persist:` block on them fails at config load with
`persist: Extra inputs are not permitted`.

The detector name is automatically appended to `path`, so `path: ./state` for a detector
named `NewValueDetector` writes to `./state/NewValueDetector/`.

#### Running under systemd

The default `path` is CWD-relative. systemd services usually run with CWD `/`,
so `./state` would resolve to `/state` (wrong location, needs root). To avoid
this, set `StateDirectory=` in your unit file  --  systemd creates `/var/lib/<dir>`
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

**Local filesystem**  --  no `storage_options` needed:

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
(`AWS_ACCESS_KEY_ID`, etc.) or instance roles  --  in which case `storage_options`
stays empty or is omitted.
