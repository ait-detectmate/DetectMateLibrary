# Overall architecture

This document describes the high-level design of DetectMateLibrary, how components interact, the data contracts they use, and guidance for deploying and extending the system. The library is built around small, composable components that operate on streaming log data and exchange strongly-typed Schema objects.

Key goals

- Clear separation of concerns (reading, parsing, detection, output).
- Stream-friendly processing with minimal buffering.
- Well-defined schema contracts so components can be composed or run as microservices.
- Easy extensibility: add new readers, parsers or detectors by subclassing core base classes.

## Components flow

The pipeline is strictly directional:

- **Parser**: consumes raw logs and produces parsed log objects (structured fields, timestamps, variables).
- **Detector**: consumes parsed logs and generates alerts / findings when rules or models match anomalous behavior.


Each arrow represents a stream of [Schema objects](schemas.md). Components are designed to run in the same process for lightweight setups or as separate services for scalable deployments.

![DIAGRAM](img/diagrams_structure.png)


## Components architecture

All components inherit from a `CoreComponent` class. This class provides all the essential functionality required for DetectMate to operate (see UML diagram below). Every [Detector](detectors.md) must inherit from `CoreDetector`, and every [Parser](parsers.md) must inherit from `CoreParser` to ensure compatibility with DetectMate.

Each component’s arguments must be stored in its corresponding configuration class. These config classes follow the same design pattern as their components and must inherit from `CoreConfig`.

![UML](img/uml_structure.png)


## Components methods

Each Core* base class exposes a small, stable API that implementations must implement or may override.

```python
class ConfigComponent(CoreConfig):
    """Contains all the arguments of the component"""


class Component(CoreComponent):
    def run(
        self, input_: List[BaseSchema] | BaseSchema, output_: BaseSchema
    ) -> bool:
    """Run the component for a specific input"""

    def train(
        self, input_: List[BaseSchema] | BaseSchema,
    ) -> None:
    """Train the component with a specific input"""

    def process(self, data: BaseSchema | bytes) -> BaseSchema | bytes | None:
    """Process the data in a stream fashion (Defined in the CoreComponent)"""

    def get_config(self) -> Dict[str, Any]:
    """"Get the configuration of the component (Defined in the CoreComponent)"""

    def update_config(self, new_config: Dict[str, Any]) -> None:
    """"Update the configuration of the component (Defined in the CoreComponent)"""
```

Go back [Index](index.md)
