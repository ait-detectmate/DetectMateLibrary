"""Contract every component (parser, detector, aggregator) must honour."""
import pytest
from detectmatelibrary.detectors.deeplog_detector import DeeplogDetector
from detectmatelibrary.detectors.random_detector import RandomDetector
from detectmatelibrary.parsers.drain import DrainParser
from detectmatelibrary.parsers.json_parser import JsonParser


class TestStatelessComponents:
    """Pipelines call the state API on every component; components that keep no
    EventPersistency answer with no-ops."""

    @pytest.mark.parametrize("component_cls", [JsonParser, DrainParser, DeeplogDetector, RandomDetector])
    def test_state_api_is_a_no_op(self, component_cls):
        with component_cls() as component:
            assert component.export_state() is None
            assert component.export_state("memory://stateless/state") is None
            component.import_state("memory://stateless/never_saved")
            component.import_state(b"not a state archive")
