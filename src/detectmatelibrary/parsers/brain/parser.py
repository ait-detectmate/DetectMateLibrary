from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary.parsers.brain.engine.core import LogParser as BrainCore
from detectmatelibrary.parsers.template_matcher._matcher_op import TemplateMatcher
from detectmatelibrary.utils.log_format_utils import get_format_variables
from detectmatelibrary import schemas

from typing import Any, cast


class BrainParserConfig(CoreParserConfig):
    """Configuration for BrainParser."""
    method_type: str = "brain_parser"
    threshold: int = 2
    delimiter: list[str] = []
    rex: list[str] = []


class BrainParser(CoreParser):
    """Brain (https://github.com/logpai/logparser/tree/main/logparser/Brain)
    wrapped as a CoreParser.

    Brain is a *batch* algorithm: it builds its word-frequency tables and
    derives templates by looking at an entire log corpus at once, whereas
    DetectMateLibrary parsers are *streaming* - ``parse()`` is called once
    per log, with no guarantee the whole corpus is available up front. To
    bridge this mismatch, Brain is not run per-log. Instead:

      * ``train()`` only buffers each log's content (no template mining yet).
      * ``post_train()`` - called once by the base component when the
        training phase ends - runs Brain's tuple-tree algorithm exactly once
        over the buffered corpus, deriving a fixed template set, then builds
        a ``TemplateMatcher`` from it and discards the buffer.
      * ``parse()`` looks up the matching template for each subsequent log
        via that ``TemplateMatcher``, in O(candidate templates) rather than
        re-running Brain. No new templates are learned after training ends.
    """

    def __init__(
        self,
        name: str = "BrainParser",
        config: BrainParserConfig | dict[str, Any] = BrainParserConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = BrainParserConfig.from_dict(config, name)

        super().__init__(name=name, config=config)
        self.config: BrainParserConfig

        self._engine = BrainCore(
            threshold=self.config.threshold,
            delimiter=self.config.delimiter,
            rex=self.config.rex,
        )
        self._buffer: list[str] = []
        self.template_matcher: TemplateMatcher | None = None

    def train(self, input_: schemas.LogSchema) -> None:  # type: ignore
        config = cast(CoreParserConfig, self.config)
        _, content = get_format_variables(
            config._regex,
            log=input_["log"],
            time_format=config.time_format,
            time_format_handler=self.time_format_handler,
        )
        self._buffer.append(content)

    def post_train(self) -> None:
        templates = self._engine.parse(self._buffer)
        self.template_matcher = TemplateMatcher(template_list=templates) if templates else None
        self._buffer = []

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema,
    ) -> None:
        if self.template_matcher is None:
            output_["template"] = "<Not Found>"
            output_["variables"] = []
            output_["EventID"] = -1
            return

        parsed = self.template_matcher(input_["log"])

        output_["template"] = parsed["EventTemplate"]
        output_["variables"] = list(parsed["Params"])
        output_["EventID"] = int(parsed["EventId"])
