from detectmatelibrary._testutils.dummy_parser import DummyParser
from detectmatelibrary._testutils.dummy_detector import DummyDetector
from detectmatelibrary._testutils.dummy_alert_aggregator import DummyAlertAggregator
from detectmatelibrary.common.detector import BufferMode
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector
from detectmatelibrary.detectors.new_value_detector import NewValueDetector
from detectmatelibrary.detectors.random_detector import RandomDetector
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
from tests.test_data import LOG_PATH, TEST_CONFIG
import yaml



config = {
    "parsers": {
        "dummy_parser": {
            "method_type": "dummy_parser",
            "auto_config": False,
            "params": {}
        }
    },
    "detectors": {
        "dummy_detector": {
            "method_type": "dummy_detector",
            "auto_config": False,
            "params": {}
        }
    },
    "alert_aggregators": {
        "dummy_alert_aggregator": {
            "method_type": "dummy_alert_aggregator",
            "auto_config": False,
            "params": {}
        }
    }
}


class TestCaseBasicPipelines:
    """This pipelines should not crash."""
    def test_basic_pipeline(self) -> None:
        parser = DummyParser(name="dummy_parser", config=config)
        detector = DummyDetector(
            name="dummy_detector",
            config=config,
            buffer_mode=BufferMode.NO_BUF,
            buffer_size=None,
        )
        aggregator = DummyAlertAggregator(name="dummy_alert_aggregator", config=config)

        gen = From.log(parser, LOG_PATH)
        for i in range(2):
            assert (parsed_log := next(gen)) is not None
            assert (processed_data:= detector.process(parsed_log)) is [None, None][i]
            assert aggregator.process(processed_data) is None
        parsed_log = next(gen)
        assert (processed_data := detector.process(parsed_log)) is not None
        assert aggregator.process(processed_data) is not None

    def test_window_pipeline(self) -> None:

        parser = DummyParser(name="dummy_parser", config=config)
        detector = DummyDetector(
            name="dummy_detector",
            config=config,
            buffer_mode=BufferMode.WINDOW,
            buffer_size=3,
        )
        aggregator = DummyAlertAggregator(name="dummy_alert_aggregator", config=config)
        gen = From.log(parser, LOG_PATH)
        for _ in range(2):
            parsed_log = next(gen)
            assert detector.process(parsed_log) is None

        parsed_log = next(gen)
        assert (processed_data:= detector.process(parsed_log)) is not None
        assert aggregator.process(processed_data) is not None

    def test_batch_pipeline(self) -> None:
        parser = DummyParser(name="dummy_parser", config=config)
        detector = DummyDetector(
            name="dummy_detector",
            config=config,
            buffer_mode=BufferMode.BATCH,
            buffer_size=3,
        )
        aggregator = DummyAlertAggregator(name="dummy_alert_aggregator", config=config)

        gen = From.log(parser, LOG_PATH)
        for _ in range(2):
            parsed_log = next(gen)
            assert detector.process(parsed_log) is None

        parsed_log = next(gen)
        assert (processed_data := detector.process(parsed_log)) is not None
        assert aggregator.process(processed_data) is not None


class TestExamples:
    def test_config_example(self) -> None:
        with open(TEST_CONFIG, 'r') as file:
            config = yaml.safe_load(file)

        # Nothing should crash

        # Parsers
        MatcherParser(config=config)

        # Detectors
        RandomDetector(config=config)

        NewValueDetector(config=config)
        NewValueDetector(config=config, name="NewValueDetector_All")

        NewValueComboDetector(config=config)
        NewValueComboDetector(config=config, name="NewValueComboDetector_All")
