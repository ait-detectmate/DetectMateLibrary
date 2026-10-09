# Quickstart

This quickstart shows how to parse a log dataset (we use data from the
[AIT Log Data Set V2.0](https://zenodo.org/records/5789064)) and then run a
detector to check whether the dataset contains anomalies. We use the
`MatcherParser` and the `RandomDetector`.

## 1. Parse the logs

```python
--8<-- "docs/examples/others/quickstart.py:parse"
```

## 2. Run the detector

```python
--8<-- "docs/examples/detectors/random_detector.py"
```

Go back [Index](../index.md)
