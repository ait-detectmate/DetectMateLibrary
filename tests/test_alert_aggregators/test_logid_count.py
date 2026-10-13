
from detectmatelibrary.alert_aggregation.logid_count import (
    Counter, LogIDCountAggegation, LogIDCountAggegationConfig
)
import detectmatelibrary.schemas as schemas


class TestCounter:
    def test_basic_count(self) -> None:
        counter = Counter(max_count=2, overall_size=10)

        assert not counter.add_and_check("a")
        assert not counter.add_and_check("b")
        assert counter.add_and_check("a")
        assert counter.add_and_check("b")

        assert not counter.add_and_check("a")  # should not generate new ones
        assert not counter.add_and_check("b")  # should not generate new ones

    def test_surpass_memory(self) -> None:
        counter = Counter(max_count=2, overall_size=2)

        assert not counter.add_and_check("a")
        assert not counter.add_and_check("b")
        assert not counter.add_and_check("c")

        assert counter.add_and_check("b")
        assert not counter.add_and_check("a")  # was rename by c 
        assert counter.add_and_check("c")
        assert counter.add_and_check("a")  

        assert not counter.add_and_check("a")  # should not generate new ones
        assert not counter.add_and_check("c")  # should not generate new ones


def generate_schema(log_id: str | list[str]) -> schemas.DetectorSchema:
    log_id = log_id if isinstance(log_id, list) else [log_id]
    return schemas.DetectorSchema({
        "detectorID": "1",
        "detectorType": "dummy",
        "alertID": "2",
        "detectionTimestamp": 0,
        "logIDs": log_id,
        "score": 0.2,
        "extractedTimestamps": [-1],
        "description": "hello there",
        "receivedTimestamp": 1,
        "alertsObtain": {"99 problems": "but logs aint one"}
    })


class TestLogIDCount:
    def test_basic_count(self):
        aggregator = LogIDCountAggegation(config=LogIDCountAggegationConfig(max_count=2))

        assert aggregator.process(generate_schema("a")) is None
        assert aggregator.process(generate_schema("b")) is None

        assert aggregator.process(generate_schema("a")) is not None
        assert aggregator.process(generate_schema("b")) is not None

        assert aggregator.process(generate_schema("a")) is None
        assert aggregator.process(generate_schema("b")) is None

    def test_basic_count_as_list(self):
        aggregator = LogIDCountAggegation(config=LogIDCountAggegationConfig(max_count=2))

        assert aggregator.process(generate_schema(["a", "b"])) is None
        assert aggregator.process(generate_schema(["a", "b"])) is not None
        assert aggregator.process(generate_schema(["a", "b"])) is None

    def test_surpass_memory(self):
        aggregator = LogIDCountAggegation(
            config=LogIDCountAggegationConfig(max_count=2, max_memory=2)
        )

        assert aggregator.process(generate_schema("a")) is None
        assert aggregator.process(generate_schema("b")) is None
        assert aggregator.process(generate_schema("c")) is None

        assert aggregator.process(generate_schema("b")) is not None
        assert aggregator.process(generate_schema("a")) is None  # was rename by c 
        assert aggregator.process(generate_schema("c")) is not None
        assert aggregator.process(generate_schema("a")) is not None

        assert aggregator.process(generate_schema("a")) is None  # should not generate new ones
        assert aggregator.process(generate_schema("c")) is None # should not generate new ones

    def test_description(self):
        aggregator = LogIDCountAggegation(config=LogIDCountAggegationConfig(max_count=1))
        alert = aggregator.process(generate_schema(["a", "b"]))

        expected = "LogID count how many times a log was count as alert."
        expected += "Logs that pass the limit count: a, b"

        assert alert["description"] == expected