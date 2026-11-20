# Pipelines

Pipelines run library components together in the same order as the service.


## Main pipeline [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/pipeline.py)]

The main pipeline functions like a standard inference pipeline. To initialize the entire system, the user only needs to provide either a configuration dictionary or the configuration classes themselves. Since the pipeline inherits from [CoreComponent](advanced/overall_architecture.md), all CoreComponent methods are also available in the pipeline class.

If `do_parsing=False`, the pipeline will take already-parsed logs as input, and the parsing step will be skipped. Likewise, if `do_aggregation=False`, the pipeline will output the detectors’ alerts directly, and the alert aggregation step will be skipped.

Configure each pipeline component with a configuration object or a dictionary. The detector list can contain both forms.

### Example 1

Run a pipeline with only one log source.

```python title="One source example"
--8<-- "docs/examples/others/pipeline.py:example_1"
```

### Example 2

Run a pipeline with multiple log sources.

```python title="Multiple source example"
--8<-- "docs/examples/others/pipeline.py:example_2"
```
