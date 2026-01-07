from detectmatelibrary.readers.kafka_consumer import KafkaConfig, KafkaReader

import pytest
import time


class TestCaseKafka:
    @pytest.mark.skip(reason="Only run when the kafka server is running")
    def test_normal(self) -> None:
        config = KafkaConfig(
            server="localhost:9092", topic="test_topic", group_id="bs"
        )
        reader = KafkaReader(config=config)

        time.sleep(5)
        assert len(reader._log_pipe) > 0, "Pipeline is empty"

        log1 = reader.process(as_bytes=False)
        assert log1.log == "hello1"

        log2 = reader.process(as_bytes=False)
        assert log2.log == "hello2"

        log3 = reader.process(as_bytes=False)
        assert log3.log == "hello3"

        assert reader.process(as_bytes=False) is None
