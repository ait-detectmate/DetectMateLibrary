# type: ignore
import os

from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector

from detectmatelibrary.utils.load_save import From

import yaml


def get_config(path: str):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config


path = "demo/data/miranda_demo_config.yaml"
detector = NewValueComboDetector(config=get_config(path))


log_topic = "logs_miranda"
parsed_topic = "parsed_miranda"
server = os.environ.get("KAFKA_SERVER", "localhost:9092")
group_id = "test"
training_size = 1000

try:
    print("Detector")

    loader = From.kafka(
        detector,
        in_topic=parsed_topic,
        server=server,
        group_id=group_id,
        as_log=False,
        do_process=False,
    )
    for i, msg in enumerate(loader):
        if i < training_size:
            detector.train(msg)
        else:
            detector.process(msg)

except KeyboardInterrupt:
    print("Detector has been stopped")
