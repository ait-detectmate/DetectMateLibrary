# Deeplog Detector

The Deeplog Detector is inspired from [Deeplog paper](https://dl.acm.org/doi/10.1145/3133956.3134015).

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Combined alert / finding |

## Description
Deep learning method that looks at the event ID sequence

## Configuration

```yaml
detectors:
    DeeplogDetector:
        method_type: deeplog_detector
        auto_config: False
        data_use_training: 10
        window_size: 3
        hyperparameters:
            Model: 
                hidden_dim: 64
                n_layers: 2
            Train: 
                seed: 0
                batch_size: 2048
                learning_rate: 0.01
                epochs: 10
                patience: 3
            Finetune: 
                - ["Model", "hidden_dim", [128, 256, 512]]
                - ["Model", "n_layers", [1, 2, 3]]
                - ["Train", "learning_rate", [0.01, 0.02, 0.03]]
```

## Example usage

```python
from detectmatelibrary.detectors.deeplog_detector import DeeplogDetector

import detectmatelibrary.schemas as schemas

detector = DeeplogDetector(name="DeeplogDetector", config=cfg)

test_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 12,
    "template": "test template",
    "variables": ["adsasd", "asdasd"],
    "logID": "2",
    "parsedLogID": "2",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"level": "CRITICAL"}
})
output = schemas.DetectorSchema()

result = detector.detect(test_data, output)

```
Go back [Index](../index.md)
