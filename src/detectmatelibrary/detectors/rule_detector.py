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

from typing import Any, Callable


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


def error_log(input_: schemas.ParserSchema, *args: list[Any]) -> tuple[bool, str]:
    vars_: dict[str, str] = input_["logFormatVariables"]
    raise_alert = "Level" in vars_ and "error" == vars_["Level"].lower()
    message = "Error found"
    return raise_alert, message


rules: dict[str, Callable[[schemas.ParserSchema, list[str]], tuple[bool, str]]] = {
    "R001 - TemplateNotFound": template_not_found,
    "R002 - SpecificKeyword": find_keyword,
    "R003 - CheckForExceptions": exceptions,
    "R004 - ErrorLevelFound": error_log,
}


class RuleNotFound(Exception):
    def __init__(self, rule: str) -> None:
        super().__init__(f"Rule -> ([{rule}]) not found")


class RuleDetectorConfig(CoreDetectorConfig):
    method_type: str = "rule_detector"
    rules: list[dict[str, list[str] | str]] = [
        {"rule": "R001 - TemplateNotFound"},
        {"rule": "R003 - CheckForExceptions"},
        {"rule": "R004 - ErrorLevelFound"},
    ]


class RuleDetector(CoreDetector):
    def __init__(
        self,
        name: str = "RuleDetector",
        config: RuleDetectorConfig | dict[str, Any] = RuleDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = RuleDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: RuleDetectorConfig

        for rule in self.config.rules:
            if rule["rule"] not in rules:
                raise RuleNotFound(rule)

    def detect(
        self, input_: schemas.ParserSchema, output_: schemas.DetectorSchema  # type: ignore
    ) -> bool:

        anomaly = False
        output_["score"] = 0

        for rule in self.config.rules:
            if "args" in rule:
                alert, msg = rules[rule["rule"]](input_, rule["args"])  # type: ignore
            else:
                alert, msg = rules[rule["rule"]](input_)  # type: ignore

            if alert:
                output_["alertsObtain"][rule["rule"]] = msg
                output_["score"] += 1

            anomaly = anomaly or alert

        return anomaly
