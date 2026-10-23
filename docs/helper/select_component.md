# Select Component

Methods that make it easy to choose components solely through configuration settings.

```python
def selectComponent(
    config: CoreConfig | dict[str, Any],
    component_type: str,
    name: Optional[str] = None
) -> CoreComponent:
    """Select a single component"""


def selectComponents(
    configs: list[CoreConfig | dict[str, Any]],
    component_type: str,
    names: Optional[list[str | None]] = None
) -> list[CoreComponent]:
    """Select multiple components"""
```

## Usage

```python
--8<-- "docs/examples/others/select_component.py:pickyou"
```
