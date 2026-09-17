# Bigram Frequency Detector

The Bigram Frequency Detector raises alerts when a variable's character bigrams (pairs of adjacent characters) appear improbable under a learned per-variable bigram frequency model. Optionally, an English-language bigram table can be consulted as a fallback for bigrams not yet seen during training.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

For each configured variable, the detector walks every observed value character-by-character (with virtual boundary characters before the first and after the last) and updates a per-(event, variable) bigram frequency table. At detect time, the average per-bigram conditional probability of a new value is computed against this table. Values scoring below `prob_thresh` are flagged. When `default_freqs` is enabled, a built-in English bigram table acts as a fallback for bigrams unseen during training.

## Configuration arguments

Arguments used in the initalization of the component.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|bigram_frequency_detector|Indicates what type of method it is.|
|auto_config|boolean|True|Runs the configuration step before the training process.|
|start_id|integer|10|Number use to start the unique ID generator.|
|data_use_training|integer, null|None|Data use for training, if None, training is not done.|
|data_use_configure|integer, null|None|Data use for configuration, if None, configuration is not done.|
|use_config_data_as_training|boolean|True|Combine the configure data in the training process if True.|
|parser|string|PARSER|Name of the parser used.|
|events|object|{}|Events configuration dict keyed by event_id.|
|global_instances|object|{}|Configuration for a specific instance within an event.|
|use_stable_vars|boolean|True|Select variables classified as STABLE when auto-configuring.|
|use_static_vars|boolean|True|Select variables classified as STATIC when auto-configuring.|
|stability_segmentation|string|count|How to segment values for stability classification. 'count' cuts segments at equal sample counts (the historical behaviour), 'time' cuts them at equal durations instead, and 'both' requires the variable to pass under both segmentations. The time-aware modes need timestamp_variable to be set.|
|timestamp_variable|string, null|None|Name of the log field holding the event timestamp, read from the record's logFormatVariables. Required by the 'time'/'both' stability segmentation modes.|
|timestamp_format|string, null|None|Expected format of timestamp_variable. If None, the format is auto-detected.|
|prob_thresh|number|0.05|Limit for the average probability of character pairs below which anomalies are reported.|
|default_freqs|boolean|False|Initialize the probabilities with default values from https://github.com/markbaggett/freq.|
|skip_repetitions|boolean|True|Only use distinct values for character-pair counting. This counteracts the problem of imbalanced word frequencies that distort the frequency table generated in a single run.|
<!-- End arguments -->

## Examples
Examples to use the component in the DetectMate environment.
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: bigram_frequency_detector
        auto_config: true
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            parser: PARSER
            global_instances: {}
            use_stable_vars: true
            use_static_vars: true
            stability_segmentation: count
            timestamp_variable: null
            timestamp_format: null
            prob_thresh: 0.05
            default_freqs: false
            skip_repetitions: true
        events: {}
```
<!-- End config -->
### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/detectors/bigram_frequency.py:example"
```

Go back [Index](../index.md)
