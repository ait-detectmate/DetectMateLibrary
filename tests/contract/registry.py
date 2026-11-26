"""Every implementation of the shared component interfaces, with a minimal
setup per class.

The contract suites in this folder parametrize over these lists, so a new
parser, detector or aggregator fails tests/contract until it is registered
here (see test_every_exported_*_is_registered in each suite).

Why every case builds its component from an explicit YAML config instead
of `Cls()`: contract checks need a deterministic, minimal setup per class
(`events` for the variable detectors, tiny hyperparameters for DeepLog and
LogBERT, `max_count` for LogIDCount, ...). Building from a YAML dict is also
how DetectMateService constructs components. Default construction is
checked on its own (`test_constructible_with_defaults`), and bug B1 (shared
default configs) by its own strict xfail tests, so no case here hides it.
"""
from dataclasses import dataclass, field
from typing import Any, Callable

import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary import alert_aggregation, detectors, parsers
from detectmatelibrary._testutils.dummy_alert_aggregator import DummyAlertAggregator
from detectmatelibrary._testutils.dummy_detector import DummyDetector
from detectmatelibrary._testutils.dummy_parser import DummyParser
from tests.support.paths import TEST_TEMPLATES

# ---- inputs -------------------------------------------------------------------


# matches template 0 of TEST_TEMPLATES
AUDIT_LINE = "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'"


def raw_log(i: int, text: str = AUDIT_LINE, source: str = "source_a") -> sc.LogSchema:
    return sc.LogSchema({"logID": str(i), "log": text, "logSource": source, "hostname": "host"})


def json_log(i: int, source: str = "source_a") -> sc.LogSchema:
    text = '{"time": "2023-11-18 10:30:00", "message": "user alice logged in", "level": "INFO"}'
    return raw_log(i, text=text, source=source)


def parsed_log(i: int, event_id: int = 1, variables: tuple[str, ...] = (), text: str = "a normal log line",
               parser_id: str = "parser") -> sc.ParserSchema:
    return sc.ParserSchema({
        "parserType": "test", "parserID": parser_id, "parsedLogID": f"p{i}", "logID": str(i),
        "eventID": event_id, "template": "user <*> from <*>", "variables": list(variables), "log": text,
        "headerVariables": {"Time": str(1_700_000_000 + i)},
    })


def event_stream(event_ids: list[int], start: int = 0) -> list[sc.ParserSchema]:
    return [parsed_log(start + k, event_id) for k, event_id in enumerate(event_ids)]


def session_log(i: int, session: str, event_id: int) -> sc.ParserSchema:
    """A parsed log of session `session` (header variable `blk`)."""
    record = parsed_log(i, event_id)
    record["headerVariables"]["blk"] = session
    return record


def alert(i: int) -> sc.DetectorSchema:
    return sc.DetectorSchema({
        "detectorID": "detector", "detectorType": "test_detector", "alertID": f"a{i}", "logIDs": [str(i)],
        "logTimestamps": [1_700_000_000 + i], "score": 1.0, "receivedTimestamp": 1_700_000_000 + i,
        "detectedTimestamp": 1_700_000_000 + i,
    })


def _variable_events(*names: str) -> dict[Any, Any]:
    return {1: {"instance": {"variables": [{"pos": k, "name": n} for k, n in enumerate(names)]}}}


# ---- cases ---------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    """One component class with a minimal YAML setup."""

    cls: type
    params: dict[str, Any] = field(default_factory=dict)
    events: dict[Any, Any] | None = None
    # further entries of the same YAML section that the component reads (JsonParser's content parser)
    extra_yaml: dict[str, Any] = field(default_factory=dict)
    binary: bool = True  # to_binary() / from_binary() work (False: disabled upstream)

    @property
    def name(self) -> str:
        return self.cls().name  # the default name; DetectMateService keys the YAML by it

    def yaml(self, name: str | None = None, persist: dict[str, Any] | None = None,
             **params: Any) -> dict[str, Any]:
        """The YAML config of this case, keyed by `name`, with extra params and
        an optional `persist:` block."""
        component = self.cls()
        entry: dict[str, Any] = {
            "method_type": component.config.method_type,
            "auto_config": False,
            "params": {**self.params, **params},
        }
        if self.events is not None:
            entry["events"] = self.events
        if persist is not None:
            entry["persist"] = persist
        return {component.config.component_type: {name or self.name: entry, **self.extra_yaml}}

    def build(self, name: str | None = None, persist: dict[str, Any] | None = None, **params: Any) -> Any:
        return self.cls(name=name or self.name, config=self.yaml(name, persist, **params))


@dataclass(frozen=True)
class ParserCase(Case):
    sample: Callable[..., sc.LogSchema] = raw_log  # (i, source=...) -> LogSchema
    headers_from_log_format: bool = True


@dataclass(frozen=True)
class DetectorCase(Case):
    """`train` is learned with data_use_training; afterwards `normal` must not
    alert and `anomalous` must (None: no such expectation)."""

    train: Callable[[], list[sc.ParserSchema]] = list
    normal: Callable[[], list[sc.ParserSchema]] | None = None
    anomalous: Callable[[], list[sc.ParserSchema]] | None = None
    window: int = 1  # how many inputs one output covers
    tracker: bool = False
    auto_config: bool = False
    session: bool = False

    def trained(self, **params: Any) -> Any:
        """A detector that has learned `train` and now detects."""
        train = self.train()
        if train:  # training counts windows, not records
            params = {"data_use_training": len(train) - self.window + 1, **params}
        detector = self.build(**params)
        for record in train:
            detector.process(record)
        return detector


@dataclass(frozen=True)
class AggregatorCase(Case):
    expects_output: bool = True


PARSERS = [
    ParserCase(parsers.DrainParser),
    ParserCase(parsers.AutoParser),
    # JsonParser reads the config of its content parser from the same YAML section, and takes its
    # header variables from the JSON fields: it drops the ones log_format extracted (question Q-D)
    ParserCase(parsers.JsonParser, sample=json_log, headers_from_log_format=False, extra_yaml={
        "JsonMatcherParser": {"method_type": "matcher_parser", "auto_config": False,
                              "params": {"path_templates": TEST_TEMPLATES}}}),
    ParserCase(parsers.TemplateCppTreeMatcher, params={"path_templates": TEST_TEMPLATES}),
    ParserCase(parsers.MatcherParser, params={"path_templates": TEST_TEMPLATES}),
    ParserCase(DummyParser),
]

_TINY_DEEPLOG = {
    "Model": {"hidden_dim": 4, "n_layers": 1},
    "Train": {"seed": 0, "batch_size": 8, "learning_rate": 0.01, "epochs": 1, "patience": 1},
    "Finetune": [],
}
_TINY_LOGBERT = {
    "Model": {"n_embed": 4, "hidden": 8, "num_heads": 1, "n_layers": 1, "dropout": 0.0, "max_len": 16},
    "Train": {"seed": 0, "batch_size": 8, "learning_rate": 0.01, "epochs": 1, "mask_per": 0.4, "alpha": 0.0,
              "patience": 1},
    "Finetune": [],
}


def _repeating(n: int) -> Callable[[], list[sc.ParserSchema]]:
    return lambda: event_stream([1, 2, 3, 4] * n)


# Event streams for the sequence and count-vector detectors (windows of 2). Each
# half of the training data teaches windows the normal probes need, (1, 2) and
# (2, 1) the first, (1, 3) and (3, 1) the second, so a federation that loses
# either half is caught. The normal probes avoid the window (1, 1) across the
# two halves, which only a detector trained on all of it has seen.
def _two_halves() -> list[sc.ParserSchema]:
    return event_stream([1, 2, 1] + [1, 3, 1])


def _needs_both_halves() -> list[sc.ParserSchema]:
    return event_stream([2, 1, 3, 1], start=10)


def _unseen_event() -> list[sc.ParserSchema]:
    return event_stream([4, 4], start=20)


DETECTORS = [
    DetectorCase(detectors.NewValueDetector, events=_variable_events("user"), tracker=True, auto_config=True,
                 train=lambda: [parsed_log(0, 1, ("alice",)), parsed_log(1, 1, ("bob",))],
                 normal=lambda: [parsed_log(10, 1, ("alice",)), parsed_log(12, 1, ("bob",))],
                 anomalous=lambda: [parsed_log(11, 1, ("mallory",))]),
    DetectorCase(detectors.NewValueComboDetector, events=_variable_events("user", "host"), tracker=True,
                 auto_config=True,
                 train=lambda: [parsed_log(0, 1, ("alice", "h1")), parsed_log(1, 1, ("bob", "h2"))],
                 normal=lambda: [parsed_log(10, 1, ("alice", "h1")), parsed_log(12, 1, ("bob", "h2"))],
                 anomalous=lambda: [parsed_log(11, 1, ("alice", "h2"))]),
    DetectorCase(detectors.CharsetDetector, events=_variable_events("user"), tracker=True, auto_config=True,
                 train=lambda: [parsed_log(0, 1, ("ab",)), parsed_log(1, 1, ("bc",))],
                 normal=lambda: [parsed_log(10, 1, ("bca",))],
                 anomalous=lambda: [parsed_log(11, 1, ("ab!",))]),
    DetectorCase(detectors.ValueRangeDetector, events=_variable_events("size"), tracker=True,
                 auto_config=True,
                 train=lambda: [parsed_log(0, 1, ("10",)), parsed_log(1, 1, ("20",))],
                 normal=lambda: [parsed_log(10, 1, ("15",))],
                 anomalous=lambda: [parsed_log(11, 1, ("1000",))]),
    # Bigram's to_binary() / from_binary() are disabled upstream ("Diasbale for now"; question Q-E)
    DetectorCase(detectors.BigramFrequencyDetector, events=_variable_events("level"), tracker=True,
                 auto_config=True, binary=False,
                 train=lambda: [parsed_log(0, 1, ("INFO",)), parsed_log(1, 1, ("INFO",))],
                 normal=lambda: [parsed_log(10, 1, ("INFO",))],
                 anomalous=lambda: [parsed_log(11, 1, ("CRITICAL",))]),
    DetectorCase(detectors.NewEventDetector, tracker=True, auto_config=True,
                 train=lambda: event_stream([1, 1, 2, 2]),
                 normal=lambda: event_stream([1, 2], start=10),
                 anomalous=lambda: event_stream([3], start=12)),
    DetectorCase(detectors.EventSequenceDetector, params={"fixed_window_size": 2}, tracker=True,
                 auto_config=True, session=True,
                 train=_two_halves, normal=_needs_both_halves, anomalous=_unseen_event),
    DetectorCase(detectors.SCVSDetector, params={"window_size": 2}, tracker=True, window=2, session=True,
                 train=_two_halves, normal=_needs_both_halves, anomalous=_unseen_event),
    DetectorCase(detectors.ECVCDetector, params={"window_size": 2, "validation_per": 0.0}, tracker=True,
                 window=2, session=True,
                 train=_two_halves, normal=_needs_both_halves, anomalous=_unseen_event),
    DetectorCase(detectors.RandomDetector,
                 events={1: {"instance": {"variables": [
                     {"pos": 0, "name": "user", "params": {"threshold": 0.0}}]}}},
                 anomalous=lambda: [parsed_log(11, 1, ("alice",))]),
    DetectorCase(detectors.RuleDetector,
                 normal=lambda: [parsed_log(10, 1)],
                 anomalous=lambda: [parsed_log(11, 1, text="connection failed with an exception")]),
    DetectorCase(DummyDetector, anomalous=lambda: event_stream([1, 1], start=11)),
    DetectorCase(detectors.DeeplogDetector, params={"window_size": 3, "hyperparameters": _TINY_DEEPLOG},
                 window=3, session=True, train=_repeating(6)),
    DetectorCase(detectors.LogBertDetector, params={"window_size": 3, "hyperparameters": _TINY_LOGBERT},
                 window=3, session=True, train=_repeating(6)),
]

# detectors whose model training takes seconds (JAX compilation); checks that train them are `slow`
SLOW_TRAINING = {detectors.DeeplogDetector, detectors.LogBertDetector}

TRACKER_DETECTORS = [case for case in DETECTORS if case.tracker]
AUTO_CONFIG_DETECTORS = [case for case in DETECTORS if case.auto_config]
SESSION_DETECTORS = [case for case in DETECTORS if case.session]

AGGREGATORS = [
    AggregatorCase(alert_aggregation.BasicConcatAggregation),
    AggregatorCase(alert_aggregation.LogIDCountAggegation, params={"max_count": 1}),
    AggregatorCase(alert_aggregation.TimeDeltaAggregation),
    # AlertBERT needs a trained model to aggregate (tested, slow, in
    # unit/alert_aggregation/test_alertbert.py); untrained, it passes alerts without output.
    AggregatorCase(alert_aggregation.AlertBERTAggregation, expects_output=False),
    AggregatorCase(DummyAlertAggregator),
]

COMPONENTS: list[Case] = [*PARSERS, *DETECTORS, *AGGREGATORS]

# The _testutils dummies are test helpers: they get the interface checks, but
# are not exported by the packages and have no documentation page.
TEST_HELPERS = {DummyParser, DummyDetector, DummyAlertAggregator}

# Exported classes deliberately not in the lists, and why.
EXCLUDED = {
    "LogBatcherParser": "needs an LLM; its wrapper is tested with a mocked LLM in unit/parsers/logbatcher/",
}


def case_id(case: Case) -> str:
    return case.cls.__name__


def cases(items: list[Any], trains: bool = False) -> list[Any]:
    """`items` as pytest params named after their class; with `trains`, the
    slow-training detectors are marked `slow`."""
    return [
        pytest.param(case, id=case_id(case),
                     marks=pytest.mark.slow if trains and case.cls in SLOW_TRAINING else ())
        for case in items
    ]
