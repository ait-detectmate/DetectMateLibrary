"""Chain C3: every detector on audit.log, driven only by process() and its
config: no direct configure() / train() / detect() calls, no forced phases.

A detector with a configure phase configures on the first TRAIN_UNTIL - 1
lines, which are replayed into training, and trains on line TRAIN_UNTIL. So
it learns exactly the first TRAIN_UNTIL lines, and post_train() runs before
the first detection line. ECVC and SCVS have no configure phase and train on
their first TRAIN_UNTIL windows, as configured in the docs.

Deterministic detectors: every alert process() returns (its logIDs) must
equal the detector's golden file in tests/test_data/golden/audit/. When the
golden files were first written they matched what the per-detector tests
expected then, e.g. the 8 labelled anomalies except 1863 for NewValue and
1863 alone for NewEvent.

DeepLog and LogBERT learn a seeded model: they must find a minimum share of
the 9 labelled anomalies and raise at most a maximum number of false alarms
(golden/audit/<detector>.thresholds.json).
"""
import pytest

from detectmatelibrary import detectors
from tests.support import golden as golden_files
from tests.support.audit import TRAIN_UNTIL

# MatcherParser settings: audit.log's header, and the preprocessing each
# detector's tests always used
LOG_FORMAT = "type=<Type> msg=audit(<Time>): <Content>"
PREPROCESS = {"remove_spaces": True, "remove_punctuation": True, "lowercase": True}
LOWERCASE = {"log_format": LOG_FORMAT, "time_format": None, "params": PREPROCESS}
PLAIN = {"log_format": LOG_FORMAT}
# the record number after the timestamp: a number for ValueRange, or left out
WITH_LINE = {**LOWERCASE, "log_format": "type=<Type> msg=audit(<Time>:<Line>): <Content>"}
WITHOUT_LINE = {**LOWERCASE, "log_format": "type=<Type> msg=audit(<Time>:*): <Content>"}

LIFECYCLE = {"auto_config": True, "data_use_configure": TRAIN_UNTIL - 1, "data_use_training": 1}
COUNT_VECTORS = {"window_size": 10, "data_use_training": TRAIN_UNTIL}


def _run(cls, parser, entry, slow=False):
    return pytest.param(cls, parser, entry, id=cls.__name__, marks=[pytest.mark.slow] if slow else [])


DETERMINISTIC = [
    _run(detectors.NewValueDetector, LOWERCASE, {"method_type": "new_value_detector", **LIFECYCLE}),
    _run(detectors.CharsetDetector, LOWERCASE, {"method_type": "charset_detector", **LIFECYCLE}),
    _run(detectors.NewValueComboDetector, PLAIN, {"method_type": "new_value_combo_detector", **LIFECYCLE}),
    _run(detectors.ValueRangeDetector, WITH_LINE, {"method_type": "value_range_detector", **LIFECYCLE}),
    _run(detectors.BigramFrequencyDetector, LOWERCASE, {
        "method_type": "bigram_frequency_detector", "params": {"skip_repetitions": True}, **LIFECYCLE}),
    _run(detectors.NewEventDetector, WITHOUT_LINE, {"method_type": "new_event_detector", **LIFECYCLE}),
    _run(detectors.EventSequenceDetector, WITHOUT_LINE, {
        "method_type": "event_sequence_detector", **LIFECYCLE}),
    _run(detectors.ECVCDetector, LOWERCASE, {
        "method_type": "ecvc_detector", "seed": 0, "validation_per": 0.0, "threshold_method": "mean",
        **COUNT_VECTORS}, slow=True),
    _run(detectors.SCVSDetector, LOWERCASE, {"method_type": "scvs_detector", **COUNT_VECTORS}, slow=True),
]


def _alerts(cls, parser, entry, audit_logs) -> list[list[str]]:
    """Every alert process() returns on audit.log, as its logIDs."""
    detector = cls(name=cls.__name__, config={"detectors": {cls.__name__: entry}})
    outputs = (detector.process(record) for record in audit_logs(parser))
    return [list(output["logIDs"]) for output in outputs if output is not None]


@pytest.mark.parametrize("cls, parser, entry", DETERMINISTIC)
def test_alerts_match_the_golden_file(cls, parser, entry, audit_logs, golden):
    golden(f"audit/{cls.__name__}", {
        "chain": "C3", "dataset": "audit.log", "train_until": TRAIN_UNTIL,
        "detector": cls.__name__, "parser": parser, "config": entry,
        "alerts": _alerts(cls, parser, entry, audit_logs),
    })


ML = [
    _run(detectors.DeeplogDetector, LOWERCASE, {
        "method_type": "deeplog_detector", "auto_config": False, "data_use_training": TRAIN_UNTIL,
        "window_size": 3,
        "hyperparameters": {
            "Model": {"hidden_dim": 64, "n_layers": 2},
            "Train": {"seed": 0, "batch_size": 2048, "learning_rate": 0.01, "epochs": 10, "patience": 3},
            "Finetune": [],
        },
    }, slow=True),
    _run(detectors.LogBertDetector, LOWERCASE, {
        "method_type": "logbert_detector", "auto_config": False, "data_use_training": TRAIN_UNTIL,
        "window_size": 10,
        "hyperparameters": {
            "Model": {"hidden": 256, "num_heads": 2, "n_layers": 4, "dropout": 0.0, "max_len": 1000},
            "Train": {"seed": 0, "batch_size": 256, "learning_rate": 0.01, "epochs": 10, "mask_per": 0.4,
                      "alpha": 0.0, "patience": 3},
            "Finetune": [],
        },
    }, slow=True),
]


@pytest.mark.parametrize("cls, parser, entry", ML)
def test_ml_detector_finds_the_labelled_anomalies(cls, parser, entry, audit_logs, anomaly_labels, request):
    """A line counts as flagged when it is in an alert's window.

    The bounds were set from one seeded run: at least one labelled
    anomaly fewer than it found, and at most 1.5 times its false alarms
    (no fewer than 5).
    """
    flagged = {log_id for alert in _alerts(cls, parser, entry, audit_logs) for log_id in alert}
    found = sorted(flagged & anomaly_labels, key=int)
    false_alarms = sorted(flagged - anomaly_labels, key=int)
    name = f"audit/{cls.__name__}.thresholds"
    settings = {
        "chain": "C3", "dataset": "audit.log", "detector": cls.__name__, "parser": parser, "config": entry,
    }

    if request.config.getoption("--update-golden"):
        path = golden_files.write(name, {
            **settings,
            "measured": {"labelled_found": found, "false_alarms": false_alarms},
            "min_labelled_found": max(len(found) - 1, 0),
            "max_false_alarms": max(5, int(1.5 * len(false_alarms))),
            "regenerate": golden_files.REGENERATE,
        })
        pytest.skip(f"golden updated: {path}")

    bounds = golden_files.read(name)
    assert {key: bounds[key] for key in settings} == golden_files.as_json(settings), \
        "the bounds were measured with other settings; regenerate them"
    assert len(found) >= bounds["min_labelled_found"], f"found only {found} of {sorted(anomaly_labels)}"
    assert len(false_alarms) <= bounds["max_false_alarms"], f"false alarms on {false_alarms}"
