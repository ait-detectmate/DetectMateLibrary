from detectmatelibrary.parsers.template_matcher import MatcherParser, MatcherParserConfig
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary.utils.key_extractor import KeyExtractor
from detectmatelibrary import schemas

from collections.abc import Mapping
from typing import Any, Iterable
import json


def iter_flatten(obj: dict[str, Any], sep: str = '.') -> Iterable[tuple[str, Any]]:
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


def flatten_dict(obj: dict[str, Any], sep: str = '.') -> dict[str, Any]:
    """Materialize a dict from iter_flatten, if you need a full flat
    mapping."""
    return dict(iter_flatten(obj, sep=sep))


class JsonParserConfig(CoreParserConfig):
    method_type: str = "json_parser"
    timestamp_name: str = "time"
    content_name: str = "message"
    content_parser: str = "JsonMatcherParser"


class JsonParser(CoreParser):
    def __init__(
        self,
        name: str = "JsonParser",
        config: JsonParserConfig | dict[str, Any] = JsonParserConfig(),
    ) -> None:

        if isinstance(config, dict):
            content_parser_name = config.get("content_parser", "JsonMatcherParser")
            content_parser_config = MatcherParserConfig.from_dict(config, content_parser_name)
            self.content_parser = MatcherParser(config=content_parser_config)
            config = JsonParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.time_extractor = KeyExtractor(key_substr=config.timestamp_name)
        self.content_extractor = KeyExtractor(key_substr=config.content_name)

    def parse(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> None:
        log = json.loads(input_["log"])
        # extract timestamp and content in the most efficient way from the json log
        timestamp = self.time_extractor.extract(obj=log, delete=True)
        content = self.content_extractor.extract(obj=log, delete=True)

        parsed = {"EventTemplate": "", "Params": [], "EventId": 0}
        # if the json also contains a message field, parse it for template and parameters
        if content:
            log_ = schemas.LogSchema({"log": content})
            parsed_content = self.content_parser.process(log_)
            parsed["EventTemplate"] = parsed_content["template"]  # type: ignore
            parsed["Params"] = parsed_content["variables"]  # type: ignore
            parsed["EventId"] = parsed_content["EventID"]  # type: ignore

        log_flat = flatten_dict(log)
        output_["logFormatVariables"].clear()  # ensure it's empty before updating
        output_["logFormatVariables"].update({k: str(v) for k, v in log_flat.items()})
        time = self.time_format_handler.parse_timestamp(timestamp, self.config.time_format)  # type: ignore
        output_["logFormatVariables"].update({"Time": time})
        output_["template"] = parsed["EventTemplate"]
        output_["variables"].extend(parsed["Params"])
        output_["EventID"] = parsed["EventId"]
