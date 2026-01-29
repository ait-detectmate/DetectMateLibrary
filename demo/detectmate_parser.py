# type: ignore
import os

from detectmatelibrary.parsers.json_parser import JsonParser

from detectmatelibrary.utils.load_save import From2To

import yaml


def get_config(path: str):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config


path = "demo/data/miranda_demo_config.yaml"
parser = JsonParser(config=get_config(path))


log_topic = "logs_miranda"
parsed_topic = "parsed_miranda"
server = os.environ.get("KAFKA_SERVER", "localhost:9092")
group_id = "test"

try:
    print("Parser")

    loader = From2To.kafka2kafka(
        parser,
        in_topic=log_topic,
        out_topic=parsed_topic,
        server=server,
        groupd_id=group_id,
        as_log=True,
        do_process=True,
    )
    for i, msg in enumerate(loader):
        parser.process(msg)

except KeyboardInterrupt:
    print("Parser has been stopped")
