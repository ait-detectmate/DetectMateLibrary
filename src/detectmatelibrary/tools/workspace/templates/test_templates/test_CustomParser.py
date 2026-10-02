import os
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
        if os.path.exists("data.json"):
            gen = From.json(parser, "data.json", do_process=False)
        else:
            gen = From.json(parser, os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "../data/logs.json"), do_process=False)
        i = 0
        while True:
            try:
                data = next(gen)
            except StopIteration:
                break
            output = parser.process(data)
            assert getattr(output, "EventID") == 2
            assert getattr(output, "template") == "This is a dummy template"
            assert getattr(output, "logFormatVariables")["Time"] == "0"
            assert getattr(output, "parserID") == "CustomParser"
            assert getattr(output, "parserType") == "custom_parser"
            assert getattr(output, "variables") == ["dummy_variable"]
            assert getattr(output, "parsedLogID") == f"CustomParser_{i + 10}"
            assert getattr(output, "logID") == str(i)
            i += 1
