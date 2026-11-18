"""Contract of the public import paths: every name a package lists in
__all__ exists, and the imports that AGENTS.md and docs/*.md show work.

The LogBatcher import in docs/development.md is left out here: importing
the module puts its config into the parsers namespace (bug B8), which the
docs contract checks on its own.
"""
import importlib

import pytest

PACKAGES = [
    "detectmatelibrary",
    "detectmatelibrary.alert_aggregation",
    "detectmatelibrary.base_alert_aggregation",
    "detectmatelibrary.base_detectors",
    "detectmatelibrary.common._config",
    "detectmatelibrary.detectors",
    "detectmatelibrary.parsers",
    "detectmatelibrary.parsers.template_matcher",
    "detectmatelibrary.schemas",
    "detectmatelibrary.schemas.connectors",
    "detectmatelibrary.utils.persistency",
    "detectmatelibrary.utils.persistency.data_structures.trackers",
    "detectmatelibrary.utils.persistency.data_structures.trackers.base",
    "detectmatelibrary.utils.persistency.data_structures.trackers.stability",
]

DOCUMENTED = {
    "detectmatelibrary.common._config": ["generate_detector_config"],
    "detectmatelibrary.base_detectors": ["TrackerDetector", "TrackerDetectorConfig", "PersistConfig"],
    "detectmatelibrary.common.detector": ["CoreDetector", "CoreDetectorConfig"],
    "detectmatelibrary.common.parser": ["CoreParser", "CoreParserConfig"],
    "detectmatelibrary.schemas": ["LogSchema", "ParserSchema", "DetectorSchema", "IncorrectSchema",
                                  "NotSupportedSchema"],
}


@pytest.mark.parametrize("package", PACKAGES)
def test_every_name_in_all_exists(package):
    module = importlib.import_module(package)
    assert [name for name in module.__all__ if not hasattr(module, name)] == []


@pytest.mark.parametrize("package, names", DOCUMENTED.items(), ids=list(DOCUMENTED))
def test_documented_imports_work(package, names):
    module = importlib.import_module(package)
    assert [name for name in names if not hasattr(module, name)] == []
