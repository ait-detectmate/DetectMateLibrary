# mypy: ignore-errors

from .drain import DrainParser, DrainConfig
from .autoparser import AutoParser, AutoParserConfig
from .json_parser import JsonParser, JsonParserConfig
from .tree_matcher import TemplateCppTreeMatcher, TemplateCppTreeMatcherConfig
from .template_matcher import MatcherParser, MatcherParserConfig


__all__ = [
    "DrainParser",
    "DrainConfig",
    "AutoParser",
    "AutoParserConfig",
    "JsonParser",
    "JsonParserConfig",
    "TemplateCppTreeMatcher",
    "TemplateCppTreeMatcherConfig",
    "MatcherParser",
    "MatcherParserConfig",
]


def __getattr__(name):
    """Load LogBatcher only when one of its exports is requested."""
    if name in {"LogBatcherParser", "LogBatcherParserConfig"}:
        from .logbatcher.parser import LogBatcherParser, LogBatcherParserConfig

        # Cache both exports for subsequent attribute access.
        globals().update(
            LogBatcherParser=LogBatcherParser,
            LogBatcherParserConfig=LogBatcherParserConfig,
        )
        return globals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
