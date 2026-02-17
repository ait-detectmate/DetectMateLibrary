# From / To helper

Utility methods to help developers load and save different schema objects. Supported formats:

- **Log files**: Read-only. Load plain log files and convert entries to LogSchema objects.
- **Binary files**: Files that store the serialized bytes of schema objects.
- **JSON files**: Files that store schema objects in JSON format.
- **YAML files**: Files that store schema objects in YAML format.

## From

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
```

### Usage

```python
parser = DummyParser()

for log in From.log(parser, in_path=log_path, do_process=False):
    print(log)
```

## To

The `To` class is responsible for saving schema objects to files.

```python
class To:
    @staticmethod
    def binary_file(out_: BaseSchema | bytes | None, out_path: str) -> bytes | None:
        """Save output schema to a binary file."""

    @staticmethod
    def json(out_: BaseSchema | None, out_path: str) -> BaseSchema | None:
        """Save output schema to a JSON file."""

    @staticmethod
    def yaml(out_: BaseSchema | None, out_path: str) -> BaseSchema | None:
        """Save output schema to a YAML file."""
```

### Usage

```python
parser = DummyParser()
for log in From.log(parser, in_path=log_path, do_process=False):
    assert To.json(log, output_path) == output_schema
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

## FromTo

The `FromTo` class loads and saves inputs and outputs in a single operation.

```python
class FromTo:
    @staticmethod
    def log2binary_file(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        """Load a log file and save it to a binary file."""

    @staticmethod
    def log2json(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        """Load a log file and save it to a JSON file."""

    @staticmethod
    def log2yaml(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        """Load a log file and save it to a YAML file."""

    @staticmethod
    def binary_file2binary_file(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a binary file and save it to a binary file."""

    @staticmethod
    def binary_file2json(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a binary file and save it to a JSON file."""

    @staticmethod
    def binary_file2yaml(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a binary file and save it to a YAML file."""

    @staticmethod
    def json2binary_file(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a JSON file and save it to a binary file."""

    @staticmethod
    def json2json(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a JSON file and save it to a JSON file."""

    @staticmethod
    def json2yaml(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a JSON file and save it to a YAML file."""

    @staticmethod
    def yaml2binary_file(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a YAML file and save it to a binary file."""

    @staticmethod
    def yaml2json(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a YAML file and save it to a JSON file."""

    @staticmethod
    def yaml2yaml(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        """Load a YAML file and save it to a YAML file."""
```

### Usage

```python
parser = DummyParser()
for parsed_log in FromTo.json2json(parser, log_path, json_path):
    pass
```

Example input data:

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

Example output data after parsing:

```json
{
    "0": {
        "template": "This is a dummy template",
        "parsedTimestamp": 1771336089,
        "EventID": 2,
        "logFormatVariables": {
            "Time": "0"
        },
        "parserID": "DummyParser",
        "parserType": "dummy_parser",
        "log": "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'",
        "variables": [
            "dummy_variable"
        ],
        "receivedTimestamp": 1771336089,
        "logID": "0",
        "__version__": "1.0.0",
        "parsedLogID": "10"
    },
    "1": {
        "template": "This is a dummy template",
        "parsedTimestamp": 1771336089,
        "EventID": 2,
        "logFormatVariables": {
            "Time": "0"
        },
        "parserID": "DummyParser",
        "parserType": "dummy_parser",
        "log": "pid=<*> uid=<*> auid=<*> ses=<*> msg='unit=<*> comm=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'",
        "variables": [
            "dummy_variable"
        ],
        "receivedTimestamp": 1771336089,
        "logID": "1",
        "__version__": "1.0.0",
        "parsedLogID": "11"
    }
}
```
Go back to [Index](index.md)
