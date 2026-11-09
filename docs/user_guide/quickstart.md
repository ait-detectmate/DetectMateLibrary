# Quickstart

This quickstart shows how to process a log dataset (we use data from the [AIT Log Data Set V2.0](https://zenodo.org/records/5789064)). We added two tutorials, [run individually](./quickstart.md#run-individually) and [run pipeline](./quickstart.md#run-all-in-a-pipeline).

## Before you start

Before starting, follow the next steps in your work directory:

1. Copy the logs from in [here](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/audit.log) and the matching templates from [here](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/test_templates.txt).

2. Install DetectMateLibrary dependency:

```bash
pip install detectmatelibrary
```

## Run individually

In the first example, we will execute the components one by one to better understand their functionality. You can follow the tutorial by copying and pasting the different code sections into your script.


### 0. Define configuration

First, we need to set up all the variables, such as the paths and the parameters used by the `DetectMate` methods. As shown below, all the methods can be initialized within the same dictionary. We will explain all the steps bellow.

```python
--8<-- "docs/examples/others/quickstart.py:config"
```

In this example, we will work with audit log data. The code below shows what the logs look like before they are processed.

```python
--8<-- "docs/examples/others/quickstart.py:other"
```

### 1. Parse the logs

By default, the logs are not parsed. To parse them, we first initialize a parser and then process the log lines.

```python
--8<-- "docs/examples/others/quickstart.py:parse"
```
Documentation of the [TemplateCppTreeMatcher](../parsers/template_tree_matcher.md).

### 2. Run the detectors
After parsing the logs, we can run the detectors to identify anomalies. In this example, we’ll use two detectors.

```python
--8<-- "docs/examples/others/quickstart.py:detectors"
```
Documentation of the [CharsetDetector](../detectors/charset.md) and [NewValueDetector](../detectors/new_value.md).

### 3. Run the alert aggregation

Finally, to combine all the alerts collected from the various detectors, an alert aggregation method is executed. This is the final output of `DetectMate`.

```python
--8<-- "docs/examples/others/quickstart.py:aggregator"
```

## Run all in a pipeline

Although you can run each method separately to gain more control over the individual steps, it isn’t required. You can also execute everything together as a single pipeline. Next, we will run the methods described earlier using the generic DetectMateLibray pipeline.

### 1. Initialize the pipeline

First, we initialze the pipeline.

```python
--8<-- "docs/examples/others/quickstart.py:pipeline"
```
Documentation of the [Pipeline](../pipeline.md).

### 2. Run the pipeline

Finally, we run the pipeline.

```python
--8<-- "docs/examples/others/quickstart.py:pipeline_run"
```
