# Pipelines

Pipelines that enable running the various components within the library, simulating the final behavior delivered by the service.


## Main pipeline

The main pipeline functions like a standard inference pipeline. To initialize the entire system, the user only needs to provide either a configuration dictionary or the configuration classes themselves. Since the pipeline inherits from [CoreComponent](advanced/overall_architecture.md), all CoreComponent methods are also available in the pipeline class.

If `do_parsing=False`, the pipeline will take already-parsed logs as input, and the parsing step will be skipped. Likewise, if `do_aggregation=False`, the pipeline will output the detectors’ alerts directly, and the alert aggregation step will be skipped.

The pipeline allows you to pass either a Config class instance or the dictionary used to initialize that Config class as arguments to the various components. For the detectors list, both methods can be combined, as shown in the example.

### Example

```python
--8<-- "docs/examples/others/pipeline.py:example_1"
```
