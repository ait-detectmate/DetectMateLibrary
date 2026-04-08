"""Tests for meaningful exception wrapping in component run/detect/parse methods."""
import pytest

from detectmatelibrary.common.core import CoreComponent, CoreConfig
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary.exceptions import (
    ComponentRunError,
    DetectMateError,
    DetectorRunError,
    ParserRunError,
)
import detectmatelibrary.schemas as schemas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ErrorInRun(CoreComponent):
    """Component whose run() always raises a bare KeyError."""

    def __init__(self) -> None:
        super().__init__(name="ErrorInRun", type_="Dummy", config=CoreConfig(),
                         input_schema=schemas.LogSchema)

    def run(self, input_, output_) -> bool:
        raise KeyError("missing_key")


class _ErrorInDetect(CoreDetector):
    """Detector whose detect() always raises a bare KeyError."""

    def __init__(self) -> None:
        super().__init__(name="ErrorInDetect", config=CoreDetectorConfig())

    def detect(self, input_, output_) -> bool:
        raise KeyError("bad_event_id")


class _ErrorInParse(CoreParser):
    """Parser whose parse() always raises a bare ValueError."""

    def __init__(self) -> None:
        super().__init__(name="ErrorInParse", config=CoreParserConfig())

    def parse(self, input_, output_) -> bool:
        raise ValueError("unrecognised_format")


_log = schemas.LogSchema({"logID": "1", "log": "test log"})
_parser_schema = schemas.ParserSchema({
    "parserType": "a",
    "EventID": 0,
    "template": "asd",
    "variables": [""],
    "logID": "0",
    "parsedLogID": "22",
    "parserID": "test",
    "log": "This is a parsed log.",
    "logFormatVariables": {"Time": "12121.12"},
})


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_detector_run_error_is_component_run_error(self) -> None:
        assert issubclass(DetectorRunError, ComponentRunError)

    def test_parser_run_error_is_component_run_error(self) -> None:
        assert issubclass(ParserRunError, ComponentRunError)

    def test_component_run_error_is_detectmate_error(self) -> None:
        assert issubclass(ComponentRunError, DetectMateError)

    def test_detectmate_error_is_exception(self) -> None:
        assert issubclass(DetectMateError, Exception)


# ---------------------------------------------------------------------------
# ComponentRunError wrapping
# ---------------------------------------------------------------------------

class TestComponentRunError:
    def test_bare_exception_in_run_is_wrapped(self) -> None:
        component = _ErrorInRun()
        with pytest.raises(ComponentRunError):
            component.process(_log)

    def test_original_cause_is_preserved(self) -> None:
        component = _ErrorInRun()
        with pytest.raises(ComponentRunError) as exc_info:
            component.process(_log)
        assert isinstance(exc_info.value.__cause__, KeyError)

    def test_component_name_in_message(self) -> None:
        component = _ErrorInRun()
        with pytest.raises(ComponentRunError) as exc_info:
            component.process(_log)
        assert "ErrorInRun" in str(exc_info.value)


# ---------------------------------------------------------------------------
# DetectorRunError wrapping
# ---------------------------------------------------------------------------

class TestDetectorRunError:
    def test_bare_exception_in_detect_is_wrapped(self) -> None:
        detector = _ErrorInDetect()
        with pytest.raises(DetectorRunError):
            detector.process(_parser_schema)

    def test_original_cause_is_preserved(self) -> None:
        detector = _ErrorInDetect()
        with pytest.raises(DetectorRunError) as exc_info:
            detector.process(_parser_schema)
        assert isinstance(exc_info.value.__cause__, KeyError)

    def test_detector_name_in_message(self) -> None:
        detector = _ErrorInDetect()
        with pytest.raises(DetectorRunError) as exc_info:
            detector.process(_parser_schema)
        assert "ErrorInDetect" in str(exc_info.value)

    def test_detector_run_error_catchable_as_component_run_error(self) -> None:
        detector = _ErrorInDetect()
        with pytest.raises(ComponentRunError):
            detector.process(_parser_schema)

    def test_detector_run_error_catchable_as_detectmate_error(self) -> None:
        detector = _ErrorInDetect()
        with pytest.raises(DetectMateError):
            detector.process(_parser_schema)


# ---------------------------------------------------------------------------
# ParserRunError wrapping
# ---------------------------------------------------------------------------

class TestParserRunError:
    def test_bare_exception_in_parse_is_wrapped(self) -> None:
        parser = _ErrorInParse()
        with pytest.raises(ParserRunError):
            parser.process(_log)

    def test_original_cause_is_preserved(self) -> None:
        parser = _ErrorInParse()
        with pytest.raises(ParserRunError) as exc_info:
            parser.process(_log)
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_parser_name_in_message(self) -> None:
        parser = _ErrorInParse()
        with pytest.raises(ParserRunError) as exc_info:
            parser.process(_log)
        assert "ErrorInParse" in str(exc_info.value)

    def test_parser_run_error_catchable_as_component_run_error(self) -> None:
        parser = _ErrorInParse()
        with pytest.raises(ComponentRunError):
            parser.process(_log)

    def test_parser_run_error_catchable_as_detectmate_error(self) -> None:
        parser = _ErrorInParse()
        with pytest.raises(DetectMateError):
            parser.process(_log)
