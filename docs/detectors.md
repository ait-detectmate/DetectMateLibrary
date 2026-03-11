
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
    comp_type: str = "detectors"
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


## Auto-configuration (optional)

Detectors can optionally support **auto-configuration** — a process where the detector automatically discovers which variables are worth monitoring, instead of requiring the user to specify them manually.

### Enabling auto-configuration

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

### Full lifecycle with auto-configuration

```python
1. configure(input_)         # call for each event in the dataset
2. set_configuration()       # finalize which variables to monitor
3. train(input_)             # call for each event in the dataset
4. detect(input_, output_)   # call for each event to detect anomalies
```

When `auto_config` is `False`, steps 1 and 2 are skipped entirely.


Go back [Index](index.md)
