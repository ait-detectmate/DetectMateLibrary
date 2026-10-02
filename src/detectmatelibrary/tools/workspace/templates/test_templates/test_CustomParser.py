from ..CustomParser import CustomParser, CustomParserConfig
from detectmatelibrary.helper.from_to import From


default_args = {
    "parsers": {
        "CustomParser": {
            "auto_config": False,
            "method_type": "custom_parser",
            "params": {},
        }
    }
}


class TestCustomParser:
    def test_initialize_default(self) -> None:
        parser = CustomParser(name="CustomParser", config=default_args)
        assert isinstance(parser, CustomParser)
        assert parser.name == "CustomParser"
        assert isinstance(parser.config, CustomParserConfig)

    def test_run_parse_method(self) -> None:
        parser = CustomParser()
        gen = From.json(parser, "data.json", do_process=False)
        i = 0
        while True:
            try:
                data = next(gen)
            except StopIteration:
                break
            output = parser.process(data)
            assert output.EventID == 2
            assert output.template == "This is a dummy template"
            assert output.logFormatVariables["Time"] == "0"
            assert output.parserID == "MyCoolParser"
            assert output.parserType == "MyCoolParser_parser"
            assert output.variables == ["dummy_variable"]
            assert output.parsedLogID == f"MyCoolParser_{i + 10}"
            assert output.logID == str(i)
            i += 1
