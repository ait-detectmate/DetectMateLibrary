from detectmatelibrary.common.alert_aggregator import CoreAlertAggregatorConfig, CoreAlertAggregator

import detectmatelibrary.schemas as schemas

import pydantic
import pytest


class MockupConfig(CoreAlertAggregatorConfig):
    pass


class MockupAlertAggregator(CoreAlertAggregator):
    def __init__(self, name: str, config: MockupConfig) -> None:
        super().__init__(
            name=name, buffer_size=1, config=config
        )

    def aggregate_alerts(self, input_, output_):
        output_["description"] = "Mockup aggregator"
        return True


dummy_config = {
    "alert_aggregators": {
        "TestAAG": {
            "method_type": "core_alert_aggregator",
            "auto_config": True,
        }
    }
}


class TestCoreAlertAggregator:
    def test_initialize_default(self) -> None:
        detector = MockupAlertAggregator(name="TestAAG", config=dummy_config)

        assert isinstance(detector, CoreAlertAggregator)
        assert detector.name == "TestAAG"
        assert isinstance(detector.config, CoreAlertAggregatorConfig)
        assert detector.input_schema == schemas.DetectorSchema
        assert detector.output_schema == schemas.OutputSchema

    def test_incorrect_config_type(self) -> None:
        dummy_config2 = {
            "alert_aggregators": {
                "TestAAG": {
                    "method_type": "core_alert_aggregator",
                    "auto_config": True,
                    "incorrect_field": 4
                }
            }
        }

        with pytest.raises(pydantic.ValidationError):
            MockupAlertAggregator(name="TestAAG", config=dummy_config2)
