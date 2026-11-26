"""Tests for detectmatelibrary.common._core_op._schema_pipeline."""
import detectmatelibrary.schemas as sc
from detectmatelibrary.common._core_op._schema_pipeline import SchemaPipeline


def test_a_schema_comes_in_as_a_copy():
    log = sc.LogSchema({"logID": "1", "log": "text"})
    is_byte, data = SchemaPipeline.preprocess(sc.LogSchema(), log)

    data["log"] = "changed"
    assert is_byte is False
    assert log["log"] == "text"


def test_bytes_come_in_as_a_schema_and_go_out_as_bytes():
    log = sc.LogSchema({"logID": "1", "log": "text"})
    template = sc.LogSchema()
    is_byte, data = SchemaPipeline.preprocess(template, log.serialize())

    assert is_byte is True
    assert data == log and data is not template
    assert SchemaPipeline.postprocess(data, is_byte=True) == log.serialize()


def test_a_schema_goes_out_unchanged():
    log = sc.LogSchema({"logID": "1"})
    assert SchemaPipeline.postprocess(log, is_byte=False) is log
