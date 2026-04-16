"""Copy and paste to create new rules.

def template_rule(
    input_: schemas.ParserSchema, *args: list[Any]
) -> tuple[bool, str]:

    raise_alert = False  # Add here rule
    message = ""  # Rule message
    return raise_alert, message
"""
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary import schemas

from typing import List, Any


def template_not_found(input_: schemas.ParserSchema, *args: list[Any]) -> tuple[bool, str]:
    raise_alert = input_["EventID"] == -1
    message = "Template was not found by the parser"
    return raise_alert, message


def find_keyword(input_: schemas.ParserSchema, args: list[str]) -> tuple[bool, str]:
    log: str = input_["log"]
    log = log.lower()

    for k in args:
        if k in log:
            return True, f"Found word '{k}' in the logs"
    return False, ""


def exceptions(input_: schemas.ParserSchema, *args: list[Any]) -> tuple[bool, str]:
    return find_keyword(input_, ["exception", "fail", "error", "raise"])


rules = {
    "TemplateNotFound": template_not_found,
    "SpecificKeyword": find_keyword,
    "CheckForExceptions": exceptions,
}


class RuleDetectorConfig(CoreDetectorConfig):
    method_type: str = "rule_detector"


class RuleDetector(CoreDetector):
    def __init__(
        self,
        name: str = "RuleDetector",
        config: RuleDetectorConfig | dict[str, Any] = RuleDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = RuleDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        return False
