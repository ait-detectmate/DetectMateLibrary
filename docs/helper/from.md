# From helper

Utility methods to help developers load different schema objects. Supported formats:

- **Log files**: Read-only. Load plain log files and convert entries to LogSchema objects.
- **Binary files**: Files that store the serialized bytes of schema objects.
- **JSON files**: Files that store schema objects in JSON format.
- **YAML files**: Files that store schema objects in YAML format.

The `From` class is responsible for loading different input formats.

```python
class From:
    @staticmethod
    def log(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        """Load logs as input schemas."""

    @staticmethod
    def binary_file(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        """Load binary files as input schemas."""

    @staticmethod
    def json(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        """Load JSON files as input schemas."""

    @staticmethod
    def yaml(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        """Load YAML files as input schemas."""

    @staticmethod
    def polars(
        component: CoreComponent,
        df: DataFrame | LazyFrame,
        do_process: bool = True,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        """
        Load Polars dataframe as input schemas follow DetectMatePerformance format.

        *  renames: allow to rename the dataframe inside the method
        """
```

### Usage

```python
--8<-- "docs/examples/others/from_to.py:example_1"
```

Go back to [Index](../index.md)
