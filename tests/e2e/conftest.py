"""Fixtures of the e2e chains: golden files, the labelled anomalies of
audit.log, and audit.log parsed once per session."""
import json
from typing import Any, Callable

import pytest

from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers.template_matcher import MatcherParser
from tests.support import golden as golden_files
from tests.support.paths import ANOMALY_LABELS, AUDIT_LOG, AUDIT_TEMPLATES


@pytest.fixture
def golden(request: pytest.FixtureRequest) -> Callable[[str, dict[str, Any]], None]:
    """A function compare(name, record): the record must equal golden file
    <name>.

    With --update-golden the file is written instead and the test is
    skipped as "golden updated".
    """
    def compare(name: str, record: dict[str, Any]) -> None:
        record = golden_files.as_json({**record, "regenerate": golden_files.REGENERATE})
        if request.config.getoption("--update-golden"):
            path = golden_files.write(name, record)
            pytest.skip(f"golden updated: {path}")
        assert record == golden_files.read(name), (
            f"output differs from golden file {golden_files.path_of(name)}; if the change is "
            f"intended, regenerate it ({golden_files.REGENERATE}) and review the diff"
        )
    return compare


@pytest.fixture(scope="session")
def anomaly_labels() -> set[str]:
    """The logIDs of the labelled anomalies in audit.log (1859-1867).

    The labels file counts lines from 1, logIDs count from 0.
    """
    with open(ANOMALY_LABELS) as f:
        return {str(json.loads(line)["line"] - 1) for line in f if line.strip()}


@pytest.fixture(scope="session")
def audit_logs() -> Callable[[dict[str, Any]], list[Any]]:
    """A function parse(parser_params): audit.log through a MatcherParser with
    these settings (log_format, preprocessing), parsed once per session and
    setting.

    Detectors don't change their input (detector contract), so tests can
    share the records.
    """
    parsed: dict[str, list[Any]] = {}

    def parse(parser_params: dict[str, Any]) -> list[Any]:
        key = json.dumps(parser_params, sort_keys=True)
        if key not in parsed:
            entry = {"method_type": "matcher_parser", "auto_config": False, **parser_params}
            entry["params"] = {**entry.get("params", {}), "path_templates": AUDIT_TEMPLATES}
            parser = MatcherParser(config={"parsers": {"MatcherParser": entry}})
            parsed[key] = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        return parsed[key]
    return parse
