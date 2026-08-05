# LogBert Detector

The LogBert Detector is inspired from [LogBert paper](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=9534113).

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Combined alert / finding |

## Description
Deep learning method that looks at the event ID sequence

## Configuration

```yaml
detectors:
    LogBertDetector:
        method_type: logbert_detector
        auto_config: False
        data_use_training: 10
        window_size: 4
        hyperparameters:
            Model: 
                hidden: 32
                num_heads: 2
                n_layers: 1
                dropout: 0.0
                max_len: 1000
            Train: 
                seed: 0
                batch_size: 256
                learning_rate: 0.01
                epochs: 10
                mask_per: 0.4
                alpha: 0.0
                patience: 3
            Finetune: 
                - ["Model", "hidden", [64, 128, 256]]
                - ["Model", "n_layers", [1, 2, 3]]
                - ["Train", "learning_rate", [0.002, 0.001, 0.005]]
```

## Example usage

```python
from detectmatelibrary.detectors.logbert_detector import LogBertDetector

import detectmatelibrary.schemas as schemas

detector = LogBertDetector(name="LogBertDetector", config=cfg)

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
