from detectmatelibrary.alert_aggregation.basic_concat import BasicConcatAggregation
from detectmatelibrary.detectors.random_detector import RandomDetector, RandomDetectorConfig
from detectmatelibrary.parsers.drain import DrainParser, DrainConfig

import detectmatelibrary.helper.select_component as selc


class TestFindFromName:
    def test_get_configs(self):
        assert (comp := selc._find_component_from_type("drain_parser", "parsers")) is not None
        assert isinstance(comp(), DrainParser)

        assert (comp := selc._find_component_from_type("random_detector", "detectors")) is not None
        assert isinstance(comp(), RandomDetector)

        assert (comp := selc._find_component_from_type(
            "basic_concat_aggregator", "alert_aggregators"
        )) is not None
        assert isinstance(comp(), BasicConcatAggregation)

        assert selc._find_component_from_type("aux", "alert_aggregators") is None


class TestPickComponets:
    def test_pick_component_dict(self):
        config = {
            "detectors": {
                "RandomDetector": {"method_type": "random_detector"}
            }
        }
        comp = selc.selectComponent(
            name="RandomDetector", config=config, component_type="detectors"
        )

        assert isinstance(comp, RandomDetector)

    def test_pick_component_dict_no_name(self):
        config = {
            "detectors": {
                "RandomDetector": {"method_type": "random_detector"}
            }
        }
        comp = selc.selectComponent(config=config, component_type="detectors")

        assert isinstance(comp, RandomDetector)

    def test_pick_component(self):
        config = DrainConfig()
        comp = selc.selectComponent(
            name="Drain", config=config, component_type="parsers"
        )

        assert isinstance(comp, DrainParser)

    def test_pick_component_no_name(self):
        config = DrainConfig()
        comp = selc.selectComponent(config=config, component_type="parsers")

        assert isinstance(comp, DrainParser)

    def test_pick_multiple_components(self):
        configs = [
            {
                "detectors": {
                    "RandomDetector": {"method_type": "random_detector"}
                }
            },
            RandomDetectorConfig(),
        ]
        names = ["RandomDetector", "RandomDetector"]

        for component in selc.selectComponents(
            configs=configs, names=names, component_type="detectors"
        ):
            assert isinstance(component, RandomDetector)

    def test_pick_multiple_components_no_names(self):
        configs = [
            {
                "detectors": {
                    "RandomDetector": {"method_type": "random_detector"}
                }
            },
            RandomDetectorConfig(),
        ]
        for component in selc.selectComponents(
            configs=configs, component_type="detectors"
        ):
            assert isinstance(component, RandomDetector)
