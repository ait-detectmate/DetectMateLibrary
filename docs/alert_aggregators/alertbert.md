# AlertBERT Alert Aggregation

The AlertBERT alert aggregator implements alert aggregation by grouping alerts according to their time-differences and embeddings of them obtained through masked-language-models, as proposed by [Karner et al.](https://doi.org/10.48550/arXiv.2602.06534).

## In/out

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](../schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](../schemas.md) | Aggregated alerts    |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ❌ | ❌ | ❌ |

## Description

This class implements alert aggregation by considering the differences between the timestamps of alerts and embeddings of alerts created by masked-language-models.

To this end, the method has two threshold parameters $\delta$ and $\theta$.
Two alerts will be assigned to the same group if the time difference between them is $\leq\delta$ and the cosine distance of their embeddings is $\leq\delta/\theta$.
The time difference is computed based on the timestamps of the last logs associated with each alert as these determine the earliest time at which the alert was detected.
Important: It is assumed that the alerts arrive in order of their timestamps!

To obtain the embeddings, in the configuration one can either specify the path of a saved masked-language-model, or one can specify the number of alerts to use as training data and the features of the alerts to use as input to the model.
Optionally, it is possible to add features to alerts in a pre-processing step by assigning them to the field `alert['alertDetails']['<feature-name>']`, which can then be specified in the configuration as `'alertDetails:<feature-name>`.

## Example

```python
--8<-- "docs/examples/alert_aggregators/alertbert.py:example_1"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/alert_aggregators/alertbert.yaml"
```

Load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `alert_aggregators:` must match the aggregator's `name`.

## Configuration arguments

All parameters this alert aggregator accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this aggregator or `shared` with other alert aggregators.

<!-- Start arguments -->

<!-- End arguments -->
