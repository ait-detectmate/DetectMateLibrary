# Overall architecture

## How things work and where data goes

This document describes the high-level design of the DetectMateLibrary, how components interact, the data contracts they use, and guidance for deploying and extending the system. The library is built around small, composable components that operate on streaming log data and exchange strongly-typed Schema objects.

Key goals

- Clear separation of concerns (reading, parsing, detection, output).
- Stream-friendly processing with minimal buffering.
- Well-defined schema contracts so components can be composed or run as microservices.
- Easy extensibility: add new readers, parsers or detectors by subclassing core base classes.

## Components flow

The pipeline is strictly directional:

- Parser: consumes raw logs and produces parsed log objects (structured fields, timestamps, variables).
- Detector: consumes parsed logs and generates alerts/findings when rules or models match anomalous behavior.
- Alert Aggregation: consumes alerts and aggregates them.

Each arrow represents a stream of Schema objects. Components are designed to run in the same process for lightweight setups or as separate services for scalable deployments.

![Components flow](../img/diagrams_structure.png)

## Components architecture

All components inherit from a `CoreComponent` class. This class provides all the essential functionality required for DetectMate to operate (see UML diagram below). Every `Detector` must inherit from `CoreDetector`, every `AlertAggregator` must inherit from `CoreAlertAggregation` and every `Parser` must inherit from `CoreParser` to ensure compatibility with DetectMate.

Each component's arguments must be stored in its corresponding configuration class. These config classes follow the same design pattern as their components and must inherit from `CoreConfig`.

![Architecture](../img/uml_structure.png)

## Components methods

Each Core* base class exposes a small, stable API that implementations must implement or may override.

```python
--8<-- "docs/examples/others/components_methods.py:read"
```

Go back [Index](../index.md)
