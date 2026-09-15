# FromTo helper

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

    @staticmethod
    def polars2binary_file(
        component: CoreComponent,
        df: DataFrame | LazyFrame,
        out_path: str,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        """Load DetectMatePerformance Dataframe to binary file"""

    @staticmethod
    def polars2json(
        component: CoreComponent,
        df: DataFrame | LazyFrame,
        out_path: str,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        """Load DetectMatePerformance Dataframe to json"""

    @staticmethod
    def polars2yaml(
        component: CoreComponent,
        df: DataFrame | LazyFrame,
        out_path: str,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        """Load DetectMatePerformance Dataframe to yaml"""
```

### Usage

```python
--8<-- "docs/examples/others/from_to.py:example_3"
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
Go back to [Index](../index.md)
