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
        params:
            prob_thresh: 0.05        # limit for the average probability of character pairs for which anomalies are reported.
            default_freqs: False     # initializes the probabilities with default values from https://github.com/markbaggett/freq.
            skip_repetitions: False  # boolean that determines whether only distinct values are used for character pair counting. This counteracts the problem of imbalanced word frequencies that distort the frequency table generated in a single aminer run.
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

```python
--8<-- "docs/examples/detectors/bigram_frequency.py:example"
```

Go back [Index](../index.md)
