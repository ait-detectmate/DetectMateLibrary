
# Components: Parsers

Parsers are components of DetectMate as show in [overall architecture](overall_architecture.md). They process unstructure logs and convert them into structured logs.

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [LogSchema](schemas.md)| Unstructured log   |
| **Output** | [ParserSchema](schemas.md)| Structured log  |


## Parsers overall

New parsers must inherent from the CoreParser class and define the **parse** and **train** method. The class structure of the **CoreParser** can be see bellow.


```python
class CoreParserConfig(CoreConfig):
    comp_type: str = "parsers"
    method_type: str = "core_parser"

    log_format: str | None = None
    time_format: str | None = None

    _regex: re.Pattern[str] | None = None


class CoreParser(CoreComponent):
    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:
        """Define in the Core parser"""

    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> bool | None:
        """Empty, must be define in the specific parser"""

    def train(self, input_: schemas.LogSchema) -> None:
        """Train the parser"""
```
To generate a new dummy parser the next structure must be follow


```python
class ParserConfig(CoreParserConfig):
    method_type: str = "parser"


class Parser(CoreParser):
    def __init__(
        self,
        name: str = "Parser",
        config: ParserConfig | dict[str, Any] = ParserConfig()
    ) -> None:

        if isinstance(config, dict):
            config = ParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        output_["EventID"] = ... # (Int) add number of the event ID
        output_["variables"].extend(["var.."])  # (Str) add variables of the log
        output_["template"] = ...  # (Str) add template of the log
```

The **run** method of the **CoreParser** will call the **parse** method you define here. **run** also take case of the rest of preprocessing and postprocessing of the logs.

## Parser methods

List of parsers:

 * [Template Matcher](parsers/template_matcher.md): match logs with a set of templates.

Go back [Index](index.md)
