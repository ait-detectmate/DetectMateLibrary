# Bigram Frequency Detector

The Bigram Frequency Detector raises alerts when a variable's character bigrams (pairs of adjacent characters) appear improbable under a learned per-variable bigram frequency model. Optionally, an English-language bigram table can be consulted as a fallback for bigrams not yet seen during training.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

For each configured variable, the detector walks every observed value character-by-character (with virtual boundary characters before the first and after the last) and updates a per-(event, variable) bigram frequency table. At detect time, the average per-bigram conditional probability of a new value is computed against this table. Values scoring below `prob_thresh` (default `0.05`) are flagged. When `default_freqs` is enabled, a built-in English bigram table acts as a fallback for bigrams unseen during training.


## Configuration example

```yaml
detectors:
    BigramFrequencyDetector:
        method_type: bigram_frequency_detector
        auto_config: False
        params: {}
        events:
            1:
                test:
                    params: {}
                    variables:
                        - pos: 0
                          name: var1
                          params:
                              threshold: 0.
                    header_variables:
                        - pos: level
                          params: {}
```


## Example usage

<!-- docs-test: skip -->
```python
from detectmatelibrary.detectors.bigram_frequency_detector import BigramFrequencyDetector, BufferMode
import detectmatelibrary.schemas as schemas

detector = BigramFrequencyDetector(name="BigramFrequencyTest", config=cfg)

parsed_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["var1"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"}
})


alert = detector.process(parsed_data)
```

Go back [Index](../index.md)
