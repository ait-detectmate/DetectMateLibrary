from detectmatelibrary import schemas

from custom_component.custom_module import CustomParser, CustomParserConfig


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
        input_data = schemas.LogSchema({"log": "test log"})
        output_data = schemas.ParserSchema()

        parser.parse(input_data, output_data)

        assert output_data.variables == ["dummy_variable"]
        assert output_data.template == "This is a dummy template"
