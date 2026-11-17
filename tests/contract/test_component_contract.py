"""Contract every component (parser, detector, aggregator) honours: the
interface that pipelines and DetectMateService rely on.

Each check runs for every class in tests/contract/registry.py. The
parser, detector and aggregator suites hold the checks for one kind of
component.
"""
import pytest
from pydantic import ValidationError

from detectmatelibrary import detectors
from detectmatelibrary.common._config._compile import MethodTypeNotMatch
from detectmatelibrary.helper.select_component import selectComponent
# from the submodule: `parsers.LogBatcherParserConfig` would cache LogBatcher in the package (bug B8)
from detectmatelibrary.parsers.logbatcher import LogBatcherParserConfig
from tests.contract.registry import COMPONENTS, DETECTORS, TEST_HELPERS, cases

PACKAGE_COMPONENTS = [case for case in COMPONENTS if case.cls not in TEST_HELPERS]
TRACKERS = {case.cls for case in DETECTORS if case.tracker}


def _yaml_entry(config: dict, case) -> dict:
    return config[case.cls().config.component_type][case.name]


@pytest.mark.parametrize("case", cases(COMPONENTS))
class TestConstruction:
    def test_constructible_with_defaults(self, case):
        component = case.cls()
        assert component.name
        assert component.config.method_type

    def test_built_from_yaml_under_any_name(self, case):
        component = case.build(name="custom_name")
        assert component.name == "custom_name"
        assert component.config.auto_config is False

    def test_unknown_setting_is_rejected(self, case):
        with pytest.raises(ValidationError, match="no_such_setting"):
            case.build(no_such_setting=1)

    def test_wrong_method_type_is_rejected(self, case):
        config = case.yaml()
        _yaml_entry(config, case)["method_type"] = "not_this_method"
        with pytest.raises(MethodTypeNotMatch):
            case.cls(name=case.name, config=config)

    def test_config_survives_a_yaml_round_trip(self, case):
        """YAML -> config -> YAML gives the same YAML (what BasicConfig.to_dict
        promises)."""
        yaml = case.build().config.to_dict("again")
        config_cls = type(case.cls().config)
        assert config_cls.from_dict(yaml, "again").to_dict("again") == yaml


@pytest.mark.parametrize("case", cases(COMPONENTS))
class TestRuntimeApi:
    def test_works_as_a_context_manager(self, case):
        component = case.build()
        with component as entered:
            assert entered is component

    def test_update_config_rejects_unknown_keys(self, case):
        with pytest.raises(ValueError, match="no_such_setting"):
            case.build().update_config({"no_such_setting": 1})

    def test_state_api(self, case):
        """Pipelines call the state API on every component: trackers answer
        with their state, all others with no-ops."""
        with case.build() as component:
            if case.cls in TRACKERS:
                state = component.export_state()
                assert isinstance(state, bytes)
                component.import_state(state)
            else:
                assert component.export_state() is None
                assert component.export_state("memory://contract/state") is None
                component.import_state("memory://contract/never_saved")
                component.import_state(b"not a state archive")


@pytest.mark.filterwarnings("ignore:To binary not implemented", "ignore:Load binary not implemented")
@pytest.mark.parametrize("case", cases([case for case in COMPONENTS if case.binary]))
def test_binary_round_trip_keeps_name_and_config(case):
    """Federation rebuilds components with from_binary() (trackers need
    allow_fed for it); the copy keeps name and config."""
    component = case.build(name="custom_name", **({"allow_fed": True} if case.cls in TRACKERS else {}))
    copy = component.from_binary(component.to_binary())

    assert type(copy) is case.cls
    assert copy.name == "custom_name"
    assert copy.config == component.config


def _undocumented(config) -> list[str]:
    rows = config.get_docs()
    return [row["Name"] for row in rows if row["Description"] in ("", "No description provided.")]


@pytest.mark.parametrize("case", cases(PACKAGE_COMPONENTS))
def test_every_setting_is_documented(case):
    """Each YAML setting has a description: the documentation pages are
    generated from these rows."""
    assert _undocumented(case.cls().config) == []


def test_every_logbatcher_setting_is_documented():
    """LogBatcherParser has no registry case (it needs an LLM) but has a
    documentation page."""
    assert _undocumented(LogBatcherParserConfig()) == []


# detectors/__init__.py imports these on first access only, so dir(detectors) doesn't list them
_LAZILY_IMPORTED = {detectors.DeeplogDetector, detectors.LogBertDetector}
_B3 = pytest.mark.xfail(strict=True, raises=ValueError,
                        reason="B3: selectComponent can't find the lazily imported DL detectors")


@pytest.mark.parametrize("case", [
    pytest.param(case, id=case.cls.__name__, marks=_B3 if case.cls in _LAZILY_IMPORTED else ())
    for case in PACKAGE_COMPONENTS
])
def test_select_component_finds_the_class(case):
    component_type = case.cls().config.component_type
    assert type(selectComponent(case.yaml(), component_type)) is case.cls


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="B1: every component class shares one default config instance")
@pytest.mark.parametrize("case", cases(COMPONENTS))
def test_default_config_is_not_shared(case):
    assert case.cls().config is not case.cls().config
