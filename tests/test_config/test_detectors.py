import pytest
import warnings
from pydantic import ValidationError

from src.config.detectors import (
    DetectorConfig,
    DetectorInstance,
    DetectorVariable,
    HeaderVariable
)


class TestDetectorInstance:
    """Test the DetectorInstance class."""

    def test_valid_instance_creation(self):
        """Test creating a valid detector instance."""
        instance = DetectorInstance(
            id="test_detector",
            event=1,
            template="Found <*> in slot <*>",
            variables=[
                DetectorVariable(id=0, name="item"),
                DetectorVariable(id=1, name="slot", params={"threshold": 0.5})
            ]
        )

        assert instance.id == "test_detector"
        assert instance.event == 1
        assert len(instance.variables) == 2
        assert instance.variables[0].name == "item"
        assert instance.variables[1].params["threshold"] == 0.5

    def test_event_all_literal(self):
        """Test that event can be 'all' literal."""
        instance = DetectorInstance(id="test", event="all")
        assert instance.event == "all"

    def test_negative_event_raises_error(self):
        """Test that negative event raises ValidationError."""
        with pytest.raises(ValidationError, match="event must be >= 0"):
            DetectorInstance(id="test", event=-1)

    def test_header_variables_with_alias(self):
        """Test header variables with alias 'header-variables'."""
        data = {
            "id": "test",
            "event": 1,
            "header-variables": [
                {"id": "Level", "params": {"threshold": 0.2}},
                {"id": "Time"}
            ]
        }

        instance = DetectorInstance.model_validate(data)
        assert len(instance.header_variables) == 2
        assert instance.header_variables[0].id == "Level"
        assert instance.header_variables[1].id == "Time"

    def test_template_variable_validation_warning(self):
        """Test warning when variable id is out of range for template."""
        with pytest.warns(UserWarning, match="Variable id 2 out of range"):
            DetectorInstance(
                id="test",
                event=1,
                template="Found <*> in slot <*>",  # Only 2 slots (0, 1)
                variables=[
                    DetectorVariable(id=0, name="item"),
                    DetectorVariable(id=2, name="out_of_range")  # Out of range
                ]
            )

    def test_negative_variable_id_warning(self):
        """Test warning when variable id is negative."""
        with pytest.warns(UserWarning, match="Variable id -1 is negative"):
            DetectorInstance(
                id="test",
                event=1,
                template="Found <*>",
                variables=[DetectorVariable(id=-1, name="negative")]
            )

    def test_no_warning_without_template(self):
        """Test no warning when no template is provided."""
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            DetectorInstance(
                id="test",
                event=1,
                variables=[DetectorVariable(id=999, name="high_id")]
            )


class TestDetectorConfig:
    """Test the DetectorConfig class."""

    def test_valid_config_with_instances(self):
        """Test creating valid config with instances."""
        config = DetectorConfig(
            type="ExampleDetector",
            parser="parser1",
            auto_config=False,
            instances=[
                DetectorInstance(id="detector1", event=1),
                DetectorInstance(id="detector2", event="all")
            ]
        )

        assert config.type == "ExampleDetector"
        assert config.parser == "parser1"
        assert not config.auto_config
        assert len(config.instances) == 2

    def test_auto_config_without_instances(self):
        """Test auto_config=True doesn't require instances."""
        config = DetectorConfig(
            type="AutoDetector",
            auto_config=True
        )

        assert config.auto_config
        assert config.instances is None

    def test_no_auto_config_requires_instances(self):
        """Test auto_config=False requires instances."""
        with pytest.raises(ValidationError, match="no explicit instances were provided"):
            DetectorConfig(
                type="ExampleDetector",
                auto_config=False
            )

    def test_no_auto_config_empty_instances_raises_error(self):
        """Test auto_config=False with empty instances raises error."""
        with pytest.raises(ValidationError, match="no explicit instances were provided"):
            DetectorConfig(
                type="ExampleDetector",
                auto_config=False,
                instances=[]
            )

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed for detector-specific
        settings."""
        config = DetectorConfig(
            type="CustomDetector",
            auto_config=True,
            custom_threshold=0.8,
            custom_params={"key": "value"}
        )

        assert config.custom_threshold == 0.8
        assert config.custom_params["key"] == "value"

    def test_parser_field_optional(self):
        """Test that parser field is optional."""
        config = DetectorConfig(
            type="StandaloneDetector",
            auto_config=True
        )

        assert config.parser is None


class TestDetectorVariable:
    """Test the DetectorVariable class."""

    def test_variable_creation(self):
        """Test creating detector variable."""
        var = DetectorVariable(
            id=0,
            name="test_var",
            params={"threshold": 0.5, "min_count": 10}
        )

        assert var.id == 0
        assert var.name == "test_var"
        assert var.params["threshold"] == 0.5

    def test_variable_minimal(self):
        """Test creating variable with minimal fields."""
        var = DetectorVariable(id=1)
        assert var.id == 1
        assert var.name is None
        assert var.params is None


class TestHeaderVariable:
    """Test the HeaderVariable class."""

    def test_header_variable_creation(self):
        """Test creating header variable."""
        header_var = HeaderVariable(
            id="Level",
            params={"threshold": 0.3}
        )

        assert header_var.id == "Level"
        assert header_var.params["threshold"] == 0.3

    def test_header_variable_minimal(self):
        """Test creating header variable with minimal fields."""
        header_var = HeaderVariable(id="Time")
        assert header_var.id == "Time"
        assert header_var.params is None
