# Drain parser

The parser is derived from the official [Drain publication](https://ieeexplore.ieee.org/document/8029742).

It also wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. When parsing large numbers of log lines in non-stream (batch) mode, it is recommended to use the performance-oriented implementation.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Configuration arguments

All parameters this parser accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this parser or `shared` with other parsers (see the [Parsers overview](../parsers.md#common-parameters-all-parsers)).

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | drain_parser | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `depth` | integer | 2 | specific | fitting description yet to find |
    | `max_childs` | integer | 10 | specific | fitting description yet to find |
    | `sim_thres` | number | 0.2 | specific | fitting description yet to find |
    | `reset_in_post_train` | boolean | False | specific | fitting description yet to find |
    | `Finetune` | array | [['depth', [1, 2, 3, 4]], ['max_childs', [10, 40]], ['sim_thres', [0.2, 0.4, 0.6, 0.8]]] | specific | fitting description yet to find |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `log_format` | string, null | None | shared | fitting description yet to find |
    | `time_format` | string, null | None | shared | fitting description yet to find |
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
parsers:
    <COMPONENT_NAME>:
        method_type: drain_parser
        auto_config: false
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            log_format: null
            time_format: null
            depth: 2
            max_childs: 10
            sim_thres: 0.2
            reset_in_post_train: false
            Finetune:
            -   - depth
                -   - 1
                    - 2
                    - 3
                    - 4
            -   - max_childs
                -   - 10
                    - 40
            -   - sim_thres
                -   - 0.2
                    - 0.4
                    - 0.6
                    - 0.8
```
<!-- End config -->

### Library usage
To use it as a python script, you can follow the example below.

Without fixing log type:

```python
--8<-- "docs/examples/parsers/drain_parser.py:example_1"
```

Simple usage (Reset = True):

```python
--8<-- "docs/examples/parsers/drain_parser.py:example_2"
```

Go back to [Index](../index.md)
