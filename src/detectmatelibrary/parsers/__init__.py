# mypy: ignore-errors
# flake8: noqa

__all__ = []

try:
    from .drain import DrainParser, DrainConfig
except ImportError:
    pass
else:
    __all__.extend(["DrainParser", "DrainConfig"])

try:
    from .autoparser import AutoParser, AutoParserConfig
except ImportError:
    pass
else:
    __all__.extend(["AutoParser", "AutoParserConfig"])

from .json_parser import JsonParser, JsonParserConfig

__all__.extend(["JsonParser", "JsonParserConfig"])

try:
    from .tree_matcher import TemplateCppTreeMatcher, TemplateCppTreeMatcherConfig
except ImportError:
    pass
else:
    __all__.extend(["TemplateCppTreeMatcher", "TemplateCppTreeMatcherConfig"])

from .template_matcher import MatcherParser, MatcherParserConfig

__all__.extend(["MatcherParser", "MatcherParserConfig"])


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
