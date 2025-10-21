"""Tests for CoreDetectorConfig, DetectorInstance, and DetectorVariable
classes.

This test suite comprehensively tests the configuration classes for detectors:

1. DetectorVariable:
   - Creation with int/string IDs
   - Parameter handling (dict, BaseModel, None)
   - Parameter serialization

2. DetectorInstance:
   - Basic creation and field validation
   - Event validation (positive int, zero, 'all', negative error)
   - Template and variable handling
   - Header variable combination
   - Warning system for invalid variable IDs and out-of-range templates

3. CoreDetectorConfig:
   - Default and custom initialization
   - Extra field validation (forbidden)
   - Instance management (add_instance method)
   - Instance counting functionality
   - Auto-config validation warnings
   - Complex scenarios and serialization roundtrip

Test Coverage: 36 tests covering all public methods, validation logic,
warning systems, and edge cases.
"""

import pytest
import warnings
from pydantic import BaseModel, ValidationError

from components.common.config.detector import DetectorInstance, DetectorVariable
from components.common.config.detector import (
    CoreDetectorConfig,
)


class SampleDetectorParams(BaseModel):
    """Sample detector parameters for testing."""
    threshold: float = 0.5
    sensitivity: int = 3
    mode: str = "default"


class TestDetectorVariable:
    """Test DetectorVariable functionality."""

    def test_create_with_int_id(self):
        """Test creating DetectorVariable with integer ID."""
        var = DetectorVariable(pos=0)
        assert var.pos == 0
        assert var.params is None

    def test_create_with_string_id(self):
        """Test creating DetectorVariable with string ID."""
        var = DetectorVariable(pos="timestamp")
        assert var.pos == "timestamp"
        assert var.params is None

    def test_create_with_dict_params(self):
        """Test creating DetectorVariable with dict parameters."""
        params = {"threshold": 0.8, "mode": "strict"}
        var = DetectorVariable(pos=1, params=params)
        assert var.pos == 1
        assert var.params == params

    def test_create_with_basemodel_params(self):
        """Test creating DetectorVariable with BaseModel parameters."""
        params = SampleDetectorParams(threshold=0.7, sensitivity=5)
        var = DetectorVariable(pos=2, params=params)
        assert var.pos == 2
        assert var.params == params

    def test_param_serialization_with_dict(self):
        """Test parameter serialization with dict."""
        params = {"key": "value"}
        var = DetectorVariable(pos=0, params=params)
        serialized = var.model_dump()
        assert serialized["params"] == params

    def test_param_serialization_with_basemodel(self):
        """Test parameter serialization with BaseModel."""
        params = SampleDetectorParams(threshold=0.9)
        var = DetectorVariable(pos=0, params=params)
        serialized = var.model_dump()
        assert serialized["params"] == {"threshold": 0.9, "sensitivity": 3, "mode": "default"}

    def test_param_serialization_with_none(self):
        """Test parameter serialization with None."""
        var = DetectorVariable(pos=0, params=None)
        serialized = var.model_dump()
        assert serialized["params"] is None


class TestDetectorInstance:
    """Test DetectorInstance functionality."""

    def test_create_basic_instance(self):
        """Test creating basic DetectorInstance."""
        instance = DetectorInstance(id="test_instance", event=1)
        assert instance.id == "test_instance"
        assert instance.event == 1
        assert instance.template is None
        assert instance.variables is None

    def test_create_with_template(self):
        """Test creating DetectorInstance with template."""
        template = "Error: <*> occurred at <*>"
        instance = DetectorInstance(id="test", event=0, template=template)
        assert instance.template == template

    def test_create_with_variables(self):
        """Test creating DetectorInstance with variables."""
        variables = [
            DetectorVariable(pos=0, params={"threshold": 0.5}),
            DetectorVariable(pos=1, params={"threshold": 0.8})
        ]
        instance = DetectorInstance(id="test", event="all", variables=variables)
        assert len(instance.variables) == 2
        assert instance.variables[0].pos == 0
        assert instance.variables[1].pos == 1

    def test_event_validation_positive_int(self):
        """Test event validation with positive integer."""
        instance = DetectorInstance(id="test", event=5)
        assert instance.event == 5

    def test_event_validation_zero(self):
        """Test event validation with zero."""
        instance = DetectorInstance(id="test", event=0)
        assert instance.event == 0

    def test_event_validation_all(self):
        """Test event validation with 'all'."""
        instance = DetectorInstance(id="test", event="all")
        assert instance.event == "all"

    def test_event_validation_negative_int(self):
        """Test event validation with negative integer (should raise error)."""
        with pytest.raises(ValidationError) as excinfo:
            DetectorInstance(id="test", event=-1)
        assert "event must be >= 0 or 'all'" in str(excinfo.value)

    def test_header_variables_combination(self):
        """Test that header variables are combined with regular variables."""
        regular_vars = [DetectorVariable(pos=0)]
        header_vars = [DetectorVariable(pos="timestamp")]

        # Using the alias for header variables
        instance = DetectorInstance(
            id="test",
            event=1,
            variables=regular_vars,
            **{"header-variables": header_vars}
        )

        # Should have both variables combined
        assert len(instance.variables) == 2
        assert any(var.pos == 0 for var in instance.variables)
        assert any(var.pos == "timestamp" for var in instance.variables)

    def test_template_variable_id_warning(self):
        """Test warning for variable ID out of range for template."""
        template = "Error at <*>"  # Only one slot
        variables = [DetectorVariable(pos=1)]  # ID 1 is out of range (should be 0)

        with pytest.warns(UserWarning) as record:
            DetectorInstance(id="test", event=1, template=template, variables=variables)

        assert len(record) == 1
        assert "Variable id 1 out of range" in str(record[0].message)

    def test_negative_variable_id_warning(self):
        """Test warning for negative variable ID (only occurs with
        template)."""
        variables = [DetectorVariable(pos=-1)]
        template = "Error at <*>"  # Template is needed for validation

        with pytest.warns(UserWarning) as record:
            DetectorInstance(id="test", event=1, template=template, variables=variables)

        assert len(record) >= 1
        # Find the warning about negative variable ID
        negative_id_warnings = [w for w in record if "Variable id -1 is negative" in str(w.message)]
        assert len(negative_id_warnings) == 1

    def test_no_warning_for_string_ids(self):
        """Test that string IDs don't trigger range warnings."""
        template = "Error at <*>"  # Only one slot
        variables = [DetectorVariable(pos="timestamp")]  # String ID should not warn

        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            # Should not raise any warnings
            instance = DetectorInstance(id="test", event=1, template=template, variables=variables)
            assert instance.variables[0].pos == "timestamp"

    def test_no_warning_without_template(self):
        """Test that negative IDs don't warn without template."""
        variables = [DetectorVariable(pos=-1)]

        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            # Should not raise any warnings since no template is provided
            instance = DetectorInstance(id="test", event=1, variables=variables)
            assert instance.variables[0].pos == -1


class TestCoreDetectorConfig:
    """Test CoreDetectorConfig functionality."""

    def test_default_initialization(self):
        """Test default initialization of CoreDetectorConfig."""
        config = CoreDetectorConfig()
        assert config.detectorID == "<PLACEHOLDER>"
        assert config.detectorType == "<PLACEHOLDER>"
        assert config.parser is None
        assert config.auto_config is False
        assert config.instances == []
        assert config._n_instances == 0  # Calculated during initialization

    def test_custom_initialization(self):
        """Test initialization with custom values."""
        config = CoreDetectorConfig(
            detectorID="custom_detector",
            detectorType="CustomType",
            parser="parser_1",
            auto_config=True
        )
        assert config.detectorID == "custom_detector"
        assert config.detectorType == "CustomType"
        assert config.parser == "parser_1"
        assert config.auto_config is True

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden (inherits from CoreConfig)."""
        with pytest.raises(ValidationError) as excinfo:
            CoreDetectorConfig(
                custom_param="custom_value",
                another_param=42
            )
        assert "Extra inputs are not permitted" in str(excinfo.value)


class TestCoreDetectorConfigInstanceManagement:
    """Test instance management in CoreDetectorConfig."""

    def test_add_instance_with_instance_object(self):
        """Test adding instance using DetectorInstance object."""
        config = CoreDetectorConfig()
        instance = DetectorInstance(id="instance_1", event=1)

        config.add_instance(instance)

        assert len(config.instances) == 1
        assert config.instances[0].id == "instance_1"
        assert config.instances[0].event == 1

    def test_add_instance_with_parameters(self):
        """Test adding instance using parameters."""
        config = CoreDetectorConfig()

        config.add_instance(pos="instance_2", event="all", template="Error: <*>")

        assert len(config.instances) == 1
        assert config.instances[0].id == "instance_2"
        assert config.instances[0].event == "all"
        assert config.instances[0].template == "Error: <*>"

    def test_add_instance_with_variables(self):
        """Test adding instance with variables."""
        config = CoreDetectorConfig()
        variables = [DetectorVariable(pos=0, params={"threshold": 0.7})]

        config.add_instance(pos="instance_3", event=2, variables=variables)

        assert len(config.instances) == 1
        assert len(config.instances[0].variables) == 1
        assert config.instances[0].variables[0].pos == 0

    def test_add_instance_missing_required_params(self):
        """Test adding instance with missing required parameters."""
        config = CoreDetectorConfig()

        with pytest.raises(ValueError) as excinfo:
            config.add_instance(pos="instance_4")  # Missing event
        assert "id and event are required" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            config.add_instance(event=1)  # Missing id
        assert "id and event are required" in str(excinfo.value)

    def test_add_instance_invalid_type(self):
        """Test adding instance with invalid type."""
        config = CoreDetectorConfig()

        with pytest.raises(TypeError) as excinfo:
            config.add_instance(instance="not_an_instance")
        assert "instance must be a DetectorInstance object" in str(excinfo.value)

    def test_get_number_of_instances_empty(self):
        """Test getting number of instances when no instances."""
        config = CoreDetectorConfig()
        assert config.get_number_of_instances() == 0

    def test_get_number_of_instances_with_variables(self):
        """Test getting number of instances counts variables."""
        config = CoreDetectorConfig()

        # Add instance with 2 variables
        config.add_instance(
            pos="instance_1",
            event=1,
            variables=[
                DetectorVariable(pos=0),
                DetectorVariable(pos=1)
            ]
        )

        # Add another instance with 3 variables
        config.add_instance(
            pos="instance_2",
            event=2,
            variables=[
                DetectorVariable(pos=0),
                DetectorVariable(pos=1),
                DetectorVariable(pos="timestamp")
            ]
        )

        assert config.get_number_of_instances() == 5  # 2 + 3 variables

    def test_calculate_n_instances_updates_count(self):
        """Test that adding instances updates the count automatically."""
        config = CoreDetectorConfig()

        # Initially should be 0
        assert config.get_number_of_instances() == 0

        # Add an instance
        config.add_instance(pos="test", event=1, variables=[DetectorVariable(pos=0)])

        # Count should update automatically
        assert config.get_number_of_instances() == 1


class TestCoreDetectorConfigValidation:
    """Test CoreDetectorConfig validation behaviors."""

    def test_auto_config_false_no_instances_warning(self):
        """Test warning when auto_config is False but no instances provided."""
        with pytest.warns(UserWarning) as record:
            config = CoreDetectorConfig(
                detectorType="TestDetector",
                auto_config=False,
                instances=[]
            )
            config  # to avoid unused variable warning

        assert len(record) == 1
        assert "has auto_config=false, but no explicit instances" in str(record[0].message)

    def test_auto_config_true_no_warning(self):
        """Test no warning when auto_config is True."""
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            # Should not raise any warnings
            config = CoreDetectorConfig(auto_config=True, instances=[])
            assert config.auto_config is True

    def test_auto_config_false_with_instances_no_warning(self):
        """Test no warning when auto_config is False but instances are
        provided."""
        instance = DetectorInstance(id="test", event=1)

        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            # Should not raise any warnings
            config = CoreDetectorConfig(
                auto_config=False,
                instances=[instance]
            )
            assert len(config.instances) == 1


class TestComplexScenarios:
    """Test complex scenarios and edge cases."""

    def test_multiple_instances_with_mixed_variables(self):
        """Test configuration with multiple instances and mixed variable
        types."""
        config = CoreDetectorConfig(
            detectorID="complex_detector",
            detectorType="ComplexDetector",
            parser="parser_1"
        )

        # Add first instance with integer ID variables
        config.add_instance(
            pos="numeric_instance",
            event=1,
            template="Error <*> at line <*>",
            variables=[
                DetectorVariable(pos=0, params=SampleDetectorParams(threshold=0.8)),
                DetectorVariable(pos=1, params={"custom": "value"})
            ]
        )

        # Add second instance with mixed ID types
        config.add_instance(
            pos="mixed_instance",
            event="all",
            variables=[
                DetectorVariable(pos="timestamp"),
                DetectorVariable(pos="level"),
                DetectorVariable(pos=0, params={"threshold": 0.5})
            ]
        )

        assert len(config.instances) == 2
        assert config.get_number_of_instances() == 5  # 2 + 3 variables
        assert config.instances[0].id == "numeric_instance"
        assert config.instances[1].id == "mixed_instance"

    def test_serialization_roundtrip(self):
        """Test that configuration can be serialized and deserialized."""
        original_config = CoreDetectorConfig(
            detectorID="test_detector",
            detectorType="TestType",
            parser="test_parser",
            auto_config=True
        )

        original_config.add_instance(
            pos="test_instance",
            event=1,
            template="Test <*>",
            variables=[
                DetectorVariable(pos=0, params=SampleDetectorParams(threshold=0.9))
            ]
        )

        # Serialize to dict
        serialized = original_config.model_dump()

        # Deserialize back
        restored_config = CoreDetectorConfig.model_validate(serialized)

        # Check that it matches
        assert restored_config.detectorID == original_config.detectorID
        assert restored_config.detectorType == original_config.detectorType
        assert restored_config.parser == original_config.parser
        assert restored_config.auto_config == original_config.auto_config
        assert len(restored_config.instances) == len(original_config.instances)
        assert restored_config.instances[0].id == original_config.instances[0].id
        assert restored_config.get_number_of_instances() == original_config.get_number_of_instances()

    def test_empty_configuration_handling(self):
        """Test handling of completely empty configuration."""
        config = CoreDetectorConfig()

        # Should handle empty state gracefully
        assert config.get_number_of_instances() == 0
        assert len(config.instances) == 0
        assert config._n_instances == 0  # Calculated during initialization

        # Should be able to add instances to empty config
        config.add_instance(pos="first", event=0)
        assert len(config.instances) == 1
        assert config.get_number_of_instances() == 0  # No variables
