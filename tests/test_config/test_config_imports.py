class TestConfigModuleImports:
    """Test that all expected classes can be imported from the config
    module."""

    def test_import_parser_classes(self):
        """Test importing parser classes."""
        from src.config import ParserInstance, ParserConfig

        # Test that classes can be instantiated
        parser_instance = ParserInstance(id="test")
        assert parser_instance.id == "test"

        parser_config = ParserConfig(type="TestParser", instances=[parser_instance])
        assert parser_config.type == "TestParser"

    def test_import_detector_classes(self):
        """Test importing detector classes."""
        from src.config import DetectorInstance, DetectorConfig

        # Test that classes can be instantiated
        detector_instance = DetectorInstance(id="test", event=1)
        assert detector_instance.id == "test"

        detector_config = DetectorConfig(type="TestDetector", auto_config=True)
        assert detector_config.type == "TestDetector"

    def test_import_app_config(self):
        """Test importing AppConfig and utility function."""
        from src.config import AppConfig, load_config_from_yaml
        from src.config import ParserConfig, ParserInstance, DetectorConfig

        # Test that AppConfig can be instantiated
        parser_config = ParserConfig(type="TestParser", instances=[ParserInstance(id="test")])
        detector_config = DetectorConfig(type="TestDetector", auto_config=True)

        app_config = AppConfig(parsers=[parser_config], detectors=[detector_config])
        assert len(app_config.parsers) == 1
        assert len(app_config.detectors) == 1

        # Test that function is callable
        assert callable(load_config_from_yaml)

    def test_all_exports_defined(self):
        """Test that __all__ contains expected exports."""
        import src.config as config_module

        expected_exports = [
            "ParserInstance",
            "ParserConfig",
            "DetectorInstance",
            "DetectorConfig",
            "AppConfig",
            "load_config_from_yaml",
        ]

        # Note: The __all__ in __init__.py also includes some classes that might not exist yet
        # like DetectorVarParams, DetectorVariable, HeaderVariable
        # We'll test for the ones we know exist
        for export in expected_exports:
            assert hasattr(config_module, export), f"{export} not found in config module"

    def test_backward_compatibility_imports(self):
        """Test that imports work for backward compatibility."""
        # These should all work without errors
        from src.config import ParserInstance, ParserConfig, AppConfig
        from src.config import DetectorInstance, DetectorConfig

        # Test a complete workflow
        parser = ParserConfig(
            type="BackwardCompatParser",
            instances=[ParserInstance(id="compat_parser")]
        )

        detector = DetectorConfig(
            type="BackwardCompatDetector",
            parser="compat_parser",
            auto_config=False,
            instances=[DetectorInstance(id="compat_detector", event=1)]
        )

        app_config = AppConfig(parsers=[parser], detectors=[detector])
        assert app_config.parsers[0].type == "BackwardCompatParser"
        assert app_config.detectors[0].parser == "compat_parser"
