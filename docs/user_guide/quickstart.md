# Quickstart

This quickstart shows how to parse a log dataset (we use data from the
[AIT Log Data Set V2.0](https://zenodo.org/records/5789064)) and then run a
detector to check whether the dataset contains anomalies. We use the
`MatcherParser` and the `RandomDetector`.

## Before you start

The example data ships with the source repository, not with the installed
package: the logs are in `tests/test_data/audit.log` and the matching templates in
`tests/test_data/audit_templates.txt`. The steps below therefore assume that you:

1. have cloned the repository and installed it (see [Installation](installation.md)):

    ```bash
    git clone https://github.com/ait-detectmate/DetectMateLibrary.git
    cd DetectMateLibrary
    uv sync
    ```

2. run the code from the repository root, the folder that contains
   `pyproject.toml`, for example with `uv run python quickstart.py`. Step 2 opens
   its configuration file with a path relative to that folder.

Step 1 writes its output files to `local/` in the repository root.

## 1. Parse the logs

```python
--8<-- "docs/examples/others/quickstart.py:parse"
```

## 2. Run the detector

```python
--8<-- "docs/examples/detectors/random_detector.py"
```

Go back [Index](../index.md)
