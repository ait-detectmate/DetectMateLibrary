# To helper

Utility methods to help developers save different schema objects. Supported formats:

- **Binary files**: Files that store the serialized bytes of schema objects.
- **JSON files**: Files that store schema objects in JSON format.
- **YAML files**: Files that store schema objects in YAML format.

The `To` class is responsible for saving schema objects to files.

```python
class To:
    @staticmethod
    def binary_file(out_: BaseSchema | bytes | None, out_path: str) -> bytes | None:
        """Save output schema to a binary file."""

    @staticmethod
    def binary_file(out_: list[BaseSchema] | list[bytes], out_path: str) -> list[bytes]:
        """Save a list of output schemas to a binary file."""

    @staticmethod
    def json(out_: BaseSchema | None, out_path: str) -> BaseSchema | None:
        """Save output schema to a JSON file."""

    @staticmethod
    def json(out_: list[BaseSchema], out_path: str) -> list[BaseSchema]:
        """Save a list of output schemas to a JSON file."""

    @staticmethod
    def yaml(out_: BaseSchema | None, out_path: str) -> BaseSchema | None:
        """Save output schema to a YAML file."""

    @staticmethod
    def yaml(out_: list[BaseSchema], out_path: str) -> list[BaseSchema] | None:
        """Save a list of output schemas to a YAML file."""
```

### Usage

```python
--8<-- "docs/examples/others/from_to.py:example_2"
```

Example JSON save file format:

```json
{
    "0": {
        "logID": "0",
        "hostname": "",
        "log": "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'",
        "logSource": "",
        "__version__": "1.0.0"
    },
    "1": {
        "logID": "1",
        "hostname": "",
        "log": "pid=<*> uid=<*> auid=<*> ses=<*> msg='unit=<*> comm=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'",
        "logSource": "",
        "__version__": "1.0.0"
    }
}
```

Go back to [Index](../index.md)
