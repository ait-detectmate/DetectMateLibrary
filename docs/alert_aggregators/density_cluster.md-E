# Density Cluster Alert Aggregation

The density-clustering-based alert aggregator is a base class to implement alert aggregation by clustering alerts according a given distance function of alerts.

## In/out

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](../schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](../schemas.md) | Aggregated alerts    |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ❌ | ❌ | ❌ | ❌ |

## Description

This class implements alert aggregation by density clustering.

### Implementation Details

This abstract class requires the implementation of 2 methods in subclasses:

1. One has to implement either the single_metric or the metric function.
The single_metric function computes the distance between 2 alerts,
while the metric function computes the distance matrix between a list of alerts.
If both functions are implemented, the metric function will be used.

2. The discard_alert_fn function must be implemented to determine which alerts
should no longer be considered for aggregation.
To this end, after each aggregation step, the discard_alert_fn
function is called with the list of relevant alerts.
It should return a list of booleans indicating which alerts should be discarded (True)
and which should be kept (False).

### Labelling of Alerts

The group labels assigned to alerts are published in the output schema as a
dictionary mapping alert IDs to group IDs in the "alertDetails" field.
Every alert is assigned a group ID immediately after it is received,
but as the aggregation progresses, groups may be merged.
This is published in the output schema as a list of messages in the "alertDetails" field.
Likewise, when a group is finished and no longer reachable from any active alert,
this is also published in the output schema as a list of messages in the "alertDetails" field.

## Example

```python
--8<-- "docs/examples/alert_aggregators/density_cluster.py:example_1"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/alert_aggregators/density_cluster.yaml"
```

Load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `alert_aggregators:` must match the aggregator's `name`.

## Configuration arguments

All parameters this alert aggregator accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this aggregator or `shared` with other alert aggregators.

<!-- Start arguments -->

<!-- End arguments -->
