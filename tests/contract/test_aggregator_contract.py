"""Contract every alert aggregator honours: DetectorSchema alerts in,
AggregateSchema out.

Each check runs for every aggregator in tests/contract/registry.py.
"""
import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary import alert_aggregation
from detectmatelibrary.schemas._classes import set_connector
from tests.contract.registry import AGGREGATORS, alert, cases

WITH_OUTPUT = [case for case in AGGREGATORS if case.expects_output]


def _aggregates(aggregator, alerts: list) -> list:
    return [out for out in map(aggregator.process, alerts) if out is not None]


def test_every_exported_aggregator_is_registered():
    exported = {name for name in alert_aggregation.__all__ if not name.endswith("Config")}
    assert exported - {case.cls.__name__ for case in AGGREGATORS} == set()


@pytest.mark.parametrize("case", cases(WITH_OUTPUT))
class TestAggregates:
    def test_aggregates_are_drawn_from_the_alerts(self, case):
        alerts = [alert(i) for i in range(4)]
        aggregates = _aggregates(case.build(), alerts)

        assert aggregates
        for aggregate in aggregates:
            assert isinstance(aggregate, sc.AggregateSchema)
            assert aggregate["aggregateID"]
            # the IDs are collected through a set, so their order is not fixed
            assert set(aggregate["alertIDs"]) <= {a["alertID"] for a in alerts}
            assert set(aggregate["logIDs"]) <= {log_id for a in alerts for log_id in a["logIDs"]}
            assert set(aggregate["detectorIDs"]) == {"detector"}
        assert len({aggregate["aggregateID"] for aggregate in aggregates}) == len(aggregates)

    def test_bytes_in_bytes_out(self, case):
        aggregates = _aggregates(case.build(), [alert(i).serialize() for i in range(4)])

        assert aggregates and all(isinstance(aggregate, bytes) for aggregate in aggregates)
        decoded = sc.AggregateSchema()
        decoded.deserialize(aggregates[0])
        assert decoded["aggregateID"]

    def test_output_is_stored_through_the_connector(self, case):
        set_connector("Verification")
        for aggregate in _aggregates(case.build(), [alert(i) for i in range(4)]):
            assert sc.AggregateSchema.from_id(aggregate["aggregateID"]) == aggregate


@pytest.mark.parametrize("case", cases(AGGREGATORS))
def test_input_is_not_modified(case):
    alerts = [alert(i) for i in range(4)]
    before = [a.copy() for a in alerts]
    _aggregates(case.build(), alerts)
    assert alerts == before


@pytest.mark.parametrize("case", cases([case for case in AGGREGATORS if not case.expects_output]))
def test_untrained_aggregator_passes_alerts_without_output(case):
    assert _aggregates(case.build(), [alert(i) for i in range(4)]) == []
