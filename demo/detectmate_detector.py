# type: ignore
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector

from detectmatelibrary.utils.load_save import From

import yaml


def get_config(path: str):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config


path = "data/miranda_demo_config.yaml"
detector = NewValueComboDetector(config=get_config(path))


log_topic = "logs_miranda"
parsed_topic = "parsed_miranda"
server = "localhost:9092"
group_id = "test"


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
    for msg in loader:
        print(msg.log)
        # Used the parsed logs as you like :D

except KeyboardInterrupt:
    print("Parser has been stopped")
