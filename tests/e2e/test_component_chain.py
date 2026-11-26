"""Chain C1: raw audit.log lines -> MatcherParser -> detector -> LogIDCount
aggregator, as separate components, once passing schema objects and once
passing bytes at every hop, as DetectMateService does.

Each detector is built with the settings of its chain C3 golden file. With
max_count=1 the aggregator emits one aggregate per anomalous line, so the
aggregated logIDs must be the alerts in that golden file, and the bytes run
must give exactly the bytes of the object run at every hop.
"""
import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary import detectors
from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegation, LogIDCountAggegationConfig
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers.template_matcher import MatcherParser
from tests.support import golden as golden_files
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

# about 4 s each: one in the default run, the rest opt-in
DETECTORS = [
    "NewValueDetector",
    *(pytest.param(name, marks=pytest.mark.slow) for name in (
        "CharsetDetector", "NewValueComboDetector", "ValueRangeDetector", "BigramFrequencyDetector",
        "NewEventDetector", "EventSequenceDetector")),
]


def _chain(detector_name: str) -> tuple:
    """A fresh parser, detector and aggregator, set up as in the C3 golden
    file."""
    setup = golden_files.read(f"audit/{detector_name}")
    entry = {"method_type": "matcher_parser", "auto_config": False, **setup["parser"]}
    entry["params"] = {**entry.get("params", {}), "path_templates": AUDIT_TEMPLATES}
    parser = MatcherParser(config={"parsers": {"MatcherParser": entry}})
    detector_class = getattr(detectors, detector_name)
    detector = detector_class(name=detector_name, config={"detectors": {detector_name: setup["config"]}})
    aggregator = LogIDCountAggegation(config=LogIDCountAggegationConfig(max_count=1))
    return parser, detector, aggregator


def _run(chain: tuple, records: list) -> list[list]:
    """The outputs of each hop: parsed logs, alerts, aggregates."""
    hops = [records]
    for component in chain:
        hops.append([output for output in map(component.process, hops[-1]) if output is not None])
    return hops[1:]


@pytest.mark.usefixtures("frozen_timestamps")  # so that two runs give the same bytes
@pytest.mark.parametrize("detector_name", DETECTORS)
def test_objects_and_bytes_give_the_golden_aggregates(detector_name):
    logs = list(From.log(MatcherParser(), in_path=AUDIT_LOG, do_process=False))

    parsed, alerts, aggregates = _run(_chain(detector_name), logs)
    byte_hops = _run(_chain(detector_name), [log.serialize() for log in logs])

    assert all(isinstance(output, sc.AggregateSchema) for output in aggregates)
    assert [list(aggregate["logIDs"]) for aggregate in aggregates] == \
        golden_files.read(f"audit/{detector_name}")["alerts"]
    for objects, as_bytes in zip((parsed, alerts, aggregates), byte_hops):
        assert as_bytes == [output.serialize() for output in objects]
