from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary.parsers.logbatcher.engine.parser import Parser as LLMParser
from detectmatelibrary.parsers.logbatcher.engine.parsing_cache import ParsingCache
from detectmatelibrary.parsers.logbatcher.engine.cluster import Cluster
from detectmatelibrary.parsers.logbatcher.engine.matching import extract_variables
from detectmatelibrary import schemas
from detectmatelibrary.constants import EVENT_ID

from typing import Any


class LogBatcherParserConfig(CoreParserConfig):
    """Configuration for LogBatcherParser."""
    method_type: str = "logbatcher_parser"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    batch_size: int = 10


class LogBatcherParser(CoreParser):
    """LLM-based log parser wrapping LogBatcher, integrated as a CoreParser."""

    def __init__(
        self,
        name: str = "LogBatcherParser",
        config: LogBatcherParserConfig | dict[str, Any] = LogBatcherParserConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = LogBatcherParserConfig.from_dict(config, name)

        super().__init__(name=name, config=config)

        llm_config = {
            "api_key": config.api_key,
            "base_url": config.base_url,
        }
        self._llm_parser = LLMParser(model=config.model, theme="default", config=llm_config)
        self._cache = ParsingCache()
        self._batch_size = config.batch_size

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema,
    ) -> None:
        log_content = input_["log"]

        template, event_id, _ = self._cache.match_event(log_content)

        if template == "NoMatch":
            cluster = Cluster()
            cluster.append_log(log_content, 0)
            cluster.batching(self._batch_size)

            template, cluster, _ = self._llm_parser.get_responce(cluster, cache_base=self._cache)

            if template not in self._cache.template_list:
                event_id, _, _ = self._cache.add_templates(template, refer_log=log_content)
            else:
                event_id = self._cache.template_list.index(template)

        variables = extract_variables(log_content, template) or ()

        output_["template"] = template
        output_["variables"].extend(list(variables))
        output_[EVENT_ID] = event_id
