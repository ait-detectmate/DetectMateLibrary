
from detectmatelibrary.common.output import CoreOutput, CoreOutputConfig
from detectmatelibrary.schemas import DetectorSchema, OutputSchema
from detectmatelibrary.utils.data_buffer import BufferMode

from typing import cast, Any
import json
import os


def save_json_file(path_folder: str, id_: str, data: dict[str, Any]) -> None:
    if not os.path.exists(path_folder):
        os.mkdir(path_folder)

    with open(f"{path_folder}/{id_}.json", "w") as json_file:
        json.dump(data, json_file)


class JSONOutputConfig(CoreOutputConfig):
    method_type: str = "json_output"
    path_folder: str = ""


class JSONOutput(CoreOutput):
    def __init__(
        self, name: str = "JsonOutput", config: JSONOutputConfig = JSONOutputConfig()
    ) -> None:

        if isinstance(config, dict):
            config = JSONOutputConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

        self.config = cast(JSONOutputConfig, self.config)
        self.test_mode: bool = False

    def do_output(self, input_: DetectorSchema, output_: OutputSchema) -> None:  # type: ignore
        output_["description"] = f"Alert description: {input_['description']}"
        output_["alertsObtain"] = input_["alertsObtain"]

        if not self.test_mode:
            save_json_file(
                path_folder=self.config.path_folder,  # type: ignore
                id_=str(input_["alertID"]),
                data=output_.as_dict(),
            )
