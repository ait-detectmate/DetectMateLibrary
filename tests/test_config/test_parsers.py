from src.config.parsers import ParserConfig, ParserInstance


class TestParserInstance:
    """Test the ParserInstance class."""

    def test_default_log_format(self):
        """Test that default log_format is '<Content>'."""
        instance = ParserInstance(id="test_parser")
        assert instance.id == "test_parser"
        assert instance.log_format == "<Content>"
        assert instance.params is None

    def test_custom_log_format(self):
        """Test setting custom log format."""
        instance = ParserInstance(
            id="custom_parser",
            log_format="[<Time>] [<Level>] <Content>"
        )
        assert instance.log_format == "[<Time>] [<Level>] <Content>"

    def test_with_params(self):
        """Test parser instance with parameters."""
        instance = ParserInstance(
            id="param_parser",
            log_format="<Content>",
            params={
                "depth": 4,
                "timeout": 30,
                "regex_pattern": r"\d+"
            }
        )

        assert instance.params["depth"] == 4
        assert instance.params["timeout"] == 30
        assert instance.params["regex_pattern"] == r"\d+"

    def test_empty_params(self):
        """Test parser instance with empty params dict."""
        instance = ParserInstance(
            id="empty_params",
            params={}
        )
        assert instance.params == {}

    def test_none_log_format_explicit(self):
        """Test explicitly setting log_format to None."""
        instance = ParserInstance(
            id="none_format",
            log_format=None
        )
        assert instance.log_format is None


class TestParserConfig:
    """Test the ParserConfig class."""

    def test_single_instance(self):
        """Test parser config with single instance."""
        config = ParserConfig(
            type="ExampleParser",
            instances=[
                ParserInstance(id="parser1", log_format="<Content>")
            ]
        )

        assert config.type == "ExampleParser"
        assert len(config.instances) == 1
        assert config.instances[0].id == "parser1"

    def test_multiple_instances(self):
        """Test parser config with multiple instances."""
        config = ParserConfig(
            type="MultiParser",
            instances=[
                ParserInstance(id="parser1", log_format="<Content>"),
                ParserInstance(id="parser2", log_format="[<Time>] <Content>"),
                ParserInstance(
                    id="parser3",
                    log_format="[<Time>] [<Level>] <Content>",
                    params={"depth": 2}
                )
            ]
        )

        assert len(config.instances) == 3
        assert config.instances[0].id == "parser1"
        assert config.instances[1].id == "parser2"
        assert config.instances[2].id == "parser3"
        assert config.instances[2].params["depth"] == 2

    def test_empty_instances_allowed(self):
        """Test that empty instances list is allowed."""
        config = ParserConfig(
            type="EmptyParser",
            instances=[]
        )
        assert config.type == "EmptyParser"
        assert len(config.instances) == 0

    def test_duplicate_instance_ids_allowed(self):
        """Test that duplicate instance IDs are allowed (validation happens at
        AppConfig level)."""
        config = ParserConfig(
            type="DuplicateParser",
            instances=[
                ParserInstance(id="same_id"),
                ParserInstance(id="same_id")
            ]
        )

        assert len(config.instances) == 2
        assert config.instances[0].id == config.instances[1].id

    def test_complex_params(self):
        """Test parser with complex nested parameters."""
        config = ParserConfig(
            type="ComplexParser",
            instances=[
                ParserInstance(
                    id="complex_parser",
                    log_format="[<Time>] [<Level>] <Content>",
                    params={
                        "regex_config": {
                            "time_pattern": r"\d{4}-\d{2}-\d{2}",
                            "level_pattern": r"(INFO|WARN|ERROR)"
                        },
                        "processing": {
                            "max_lines": 1000,
                            "buffer_size": 8192
                        },
                        "features": ["timestamp", "level", "content"]
                    }
                )
            ]
        )

        params = config.instances[0].params
        assert params["regex_config"]["time_pattern"] == r"\d{4}-\d{2}-\d{2}"
        assert params["processing"]["max_lines"] == 1000
        assert "timestamp" in params["features"]
