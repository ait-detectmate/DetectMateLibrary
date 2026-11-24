from detectmatelibrary.parsers.template_matcher import (
    MatcherParser,
    MatcherParserConfig,
)
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary.utils.key_extractor import KeyExtractor
from detectmatelibrary.tools.logging import logger
from detectmatelibrary import schemas

from collections.abc import Mapping
from typing import Any, Iterable
import json
from pydantic import Field

# eventID of a log without a message field (-1 is a message that matches no template)
NO_MESSAGE_EVENT_ID = -2


def iter_flatten(obj: dict[str, Any], sep: str = ".") -> Iterable[tuple[str, Any]]:
    """Iteratively flattens a nested dict/list JSON-like object. Yields
    (flat_key, value) pairs.

    Example:
        {"a": {"b": 1}, "c": [10, 20]}
    yields:
        ("a.b", 1)
        ("c.0", 10)
        ("c.1", 20)
    """
    stack = [("", obj)]  # (prefix_string, current_value)
    sep = str(sep)
    while stack:
        prefix, current = stack.pop()
        if isinstance(current, Mapping):
            for k, v in current.items():
                k = str(k)
                new_key = k if not prefix else prefix + sep + k
                stack.append((new_key, v))
        elif isinstance(current, list) or isinstance(current, tuple):
            for idx, item in enumerate(current):
                idx_str = str(idx)
                new_key = idx_str if not prefix else prefix + sep + idx_str
                stack.append((new_key, item))
        else:
            yield prefix, current


def flatten_dict(obj: dict[str, Any], sep: str = ".") -> dict[str, Any]:
    """Materialize a dict from iter_flatten, if you need a full flat
    mapping."""
    return dict(iter_flatten(obj, sep=sep))


class JsonParserConfig(CoreParserConfig):
    method_type: str = Field(default="json_parser", description="Indicates what type of method it is.")
    timestamp_name: str = Field(
        default="time", description="fitting description yet to find"
    )
    content_name: str = Field(
        default="message", description="fitting description yet to find"
    )
    content_parser: str = Field(
        default="JsonMatcherParser", description="fitting description yet to find"
    )


class JsonParser(CoreParser):
    def __init__(
        self,
        name: str = "JsonParser",
        config: JsonParserConfig | dict[str, Any] = JsonParserConfig(),
    ) -> None:

        if isinstance(config, dict):
            cfg_dict = JsonParserConfig.from_dict(config, name)
            content_parser_config = MatcherParserConfig.from_dict(
                config, cfg_dict.content_parser
            )
            self.content_parser = MatcherParser(config=content_parser_config)
            config = cfg_dict
        else:
            # a config object cannot define the content parser: use one without templates
            self.content_parser = MatcherParser()
        super().__init__(name=name, config=config)
        self.config: JsonParserConfig
        self._warn_no_templates = self.content_parser.config.path_templates is None

        self.time_extractor = KeyExtractor(key_substr=config.timestamp_name)
        self.content_extractor = KeyExtractor(key_substr=config.content_name)

    def parse(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> None:
        log = json.loads(input_["log"])
        # extract timestamp and content in the most efficient way from the json log
        timestamp = self.time_extractor.extract(obj=log, delete=True)
        content = self.content_extractor.extract(obj=log, delete=True)

        parsed = {"EventTemplate": "", "Params": [], "EventId": NO_MESSAGE_EVENT_ID}
        # if the json also contains a message field, parse it for template and parameters
        if content:
            if self._warn_no_templates:
                logger.warning(
                    f"<<{self.name}>> the content parser has no templates, so every message gets "
                    "eventID -1. Define the content parser with path_templates in a config dict."
                )
                self._warn_no_templates = False
            log_ = schemas.LogSchema({"log": content})
            parsed_content = self.content_parser.process(log_)
            parsed["EventTemplate"] = parsed_content["template"]  # type: ignore
            parsed["Params"] = parsed_content["variables"]  # type: ignore
            parsed["EventId"] = parsed_content["eventID"]  # type: ignore

        log_flat = flatten_dict(log)
        output_["headerVariables"].clear()  # ensure it's empty before updating
        output_["headerVariables"].update({k: str(v) for k, v in log_flat.items()})
        time = self.time_format_handler.parse_timestamp(
            str(timestamp), self.config.time_format
        )
        output_["headerVariables"].update({"Time": time})
        output_["template"] = parsed["EventTemplate"]
        output_["variables"].extend(parsed["Params"])
        output_["eventID"] = parsed["EventId"]
