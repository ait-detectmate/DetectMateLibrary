
# Components: Detectors

Detectors are components of DetectMate as show in [overall architecture](overall_architecture.md). They process structured logs from the [parsers](parsers.md) and return alerts if they find anomalies in the data.

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [ParserSchema](schemas.md)| Structured log  |
| **Output** | [DetectorSchema](schemas.md) | Alerts produced |


## Detectors overall

New detectors must inherent from the CoreDetector class and define the **detect** and **train** method. The class structure of the **CoreDetect** can be see bellow.


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
To generate a new detector the next structure must be follow


```python
class DetectorConfig(CoreDetectorConfig):
    method_type: str = "detector"


class Detector(CoreDetector):
    def __init__(
        self,
        name: str = "Detector",
        config: DetectorConfig | dict[str, Any] = DetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:

        output_["description"] = ...  # (Str) Description of the detector
        output_["score"] = ...  # (Float) Score of the alert
        output_["alertsObtain"] = ... # (Dict[str, str] Extra information of the alert)

        return True  # True if an alert was found, else False
```

The **run** method of the **CoreParser** will call the **parse** method you define here. **run** also take case of the rest of preprocessing and postprocessing of the logs.

To configure the number of logs receive as input, you need to configure the [buffer](auxiliar/input_buffer.md) in the initialization of the Detector.

## Detectors methods

List of detectors:

* [New Value](detectors/new_value.md): Detect new values in the variables in the logs.
* [Combo Detector](detectors/combo.md): Detect new combination of variables in the logs.

Go back [Index](index.md)
