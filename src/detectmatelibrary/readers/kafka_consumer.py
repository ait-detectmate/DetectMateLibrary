from detectmatelibrary.common.reader import CoreReaderConfig, CoreReader

from detectmatelibrary import schemas

from kafka import KafkaConsumer
from typing import Optional
import threading


class KafkaConfig(CoreReaderConfig):
    file: str = "<PLACEHOLDER>"
    method_type: str = "log_file_reader"

    server: str = "<PLACEHOLDER>"
    topic: str = "<PLACEHOLDER>"
    group_id: str = "<PLACEHOLDER>"


def kafka_consumer(config: KafkaConfig, log_pipe: list[str]) -> None:
    consumer = KafkaConsumer(
        config.topic,
        bootstrap_servers=config.server,
        group_id=config.group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=1000
    )

    try:
        while True:
            for msg in consumer:
                log_pipe.append(msg.value.decode("utf-8"))
    except KeyboardInterrupt:
        print("shutting down consumer")
    finally:
        consumer.close()


class KafkaReader(CoreReader):
    def __init__(
        self,
        name: str = "Kafka_reader",
        config: Optional[KafkaConfig | dict] = KafkaConfig(),  # type: ignore
    ) -> None:

        if isinstance(config, dict):
            config = KafkaConfig.from_dict(config, name)

        super().__init__(name=name, config=config)
        self._log_pipe: list[str] = []
        self._init_consumer()

    def _init_consumer(self) -> None:
        cfg = self.config
        pipe = self._log_pipe

        thread = threading.Thread(
            target=kafka_consumer,
            args=(cfg, pipe),
            daemon=True,
            name=f"kafka_consumer_{self.name}"
        )
        thread.start()
        self._consumer_thread = thread

    def read(self, output_: schemas.LogSchema) -> bool:
        if len(self._log_pipe) == 0:
            return False

        output_["log"] = self._log_pipe.pop(0)

        return True
