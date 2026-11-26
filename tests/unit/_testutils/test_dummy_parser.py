"""Tests for detectmatelibrary._testutils.dummy_parser: the fixed output that
other tests rely on (its interface is checked by tests/contract)."""
import detectmatelibrary.schemas as sc
from detectmatelibrary._testutils.dummy_parser import DummyParser


def test_every_log_gets_the_same_event():
    for text in ("test log", "something else entirely"):
        parsed = DummyParser().process(sc.LogSchema({"logID": "1", "log": text}))

        assert parsed["eventID"] == 2
        assert list(parsed["variables"]) == ["dummy_variable"]
        assert parsed["template"] == "This is a dummy template"
