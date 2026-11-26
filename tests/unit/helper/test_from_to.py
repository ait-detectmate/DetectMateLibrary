"""Tests for detectmatelibrary.helper.from_to."""
from detectmatelibrary.helper.from_to import From, To, FromTo
from detectmatelibrary._testutils.dummy_detector import DummyDetector
from detectmatelibrary._testutils.dummy_parser import DummyParser
from tests.support.paths import AUDIT_TEMPLATES
import detectmatelibrary.schemas as sc
import detectmateperformance as dmp
import polars as pl
from ast import literal_eval
import json
import yaml
import os

import pytest


expected_log = "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> "
expected_log += "acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'"
log_path = AUDIT_TEMPLATES

# Output files, relative to the test's working directory: every test runs in its
# own temporary directory (tests/conftest.py), so nothing is written next to the
# test data and nothing has to be cleaned up.
DUMMY_TXT_PATH, DUMMY_TXT_PATH2 = "dummy.txt", "dummy2.txt"
DUMMY_JSON_PATH, DUMMY_JSON_PATH2 = "dummy.json", "dummy2.json"
DUMMY_YAML_PATH, DUMMY_YAML_PATH2 = "dummy.yaml", "dummy2.yaml"
binary_path, binary_path2 = DUMMY_TXT_PATH, DUMMY_TXT_PATH2
json_path, json_path2 = DUMMY_JSON_PATH, DUMMY_JSON_PATH2
yaml_path, yaml_path2 = DUMMY_YAML_PATH, DUMMY_YAML_PATH2


class TestCaseTo:
    def test_tobinary(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log = next(gen)
        assert To.binary_file(log, DUMMY_TXT_PATH) == log.serialize()

        log = next(gen)
        assert To.binary_file(log.serialize(), DUMMY_TXT_PATH) == log.serialize()

        assert To.binary_file(None, DUMMY_TXT_PATH) is None

        with open(DUMMY_TXT_PATH, "r") as f:
            assert len(f.readlines()) == 2

    def test_tobinary_as_list(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)
        logs = [log.serialize() for log in gen]

        assert To.binary_file(logs, binary_path) == logs
        with open(binary_path, "r") as f:
            assert len(f.readlines()) == 9

    def test_tojson(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log = next(gen)
        assert To.json(log, DUMMY_JSON_PATH) == log

        log = next(gen)
        assert To.json(log, DUMMY_JSON_PATH) == log

        assert To.json(None, DUMMY_JSON_PATH) is None

        with open(DUMMY_JSON_PATH, "r") as f:
            assert len(json.load(f)) == 2

    def test_tojson_list(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)
        logs = [log for log in gen]

        assert To.json(logs, json_path) == logs
        with open(json_path, "r") as f:
            assert len(json.load(f)) == 9

    def test_toyaml(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log = next(gen)
        assert To.yaml(log, DUMMY_YAML_PATH) == log

        log = next(gen)
        assert To.yaml(log, DUMMY_YAML_PATH) == log

        assert To.yaml(None, DUMMY_YAML_PATH) is None

        with open(DUMMY_YAML_PATH, "r") as f:
            assert len(yaml.safe_load(f)) == 2

    def test_toyaml_list(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)
        logs = [log for log in gen]

        assert To.yaml(logs, yaml_path) == logs
        with open(yaml_path, "r") as f:
            assert len(yaml.safe_load(f)) == 9


class TestCaseFrom:
    def test_fromlog_no_process(self):
        parser = DummyParser()

        log = next(From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False))

        assert log.log == expected_log
        assert isinstance(log, sc.LogSchema)

    def test_fromlog(self):
        parser = DummyParser()

        log = next(From.log(parser, in_path=AUDIT_TEMPLATES, do_process=True))

        assert log.log == expected_log
        assert isinstance(log, sc.ParserSchema)

        log = next(From.log(
            parser, in_path=AUDIT_TEMPLATES, do_process=True, constant_fields={"logID": "hi"}
        ))

        assert log.logID == "hi"

    def test_frombinary(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log1 = To.binary_file(next(gen), DUMMY_TXT_PATH)
        log2 = next(From.binary_file(parser, DUMMY_TXT_PATH, do_process=False))

        assert log1 == log2.serialize()

        log = next(From.binary_file(
            parser, DUMMY_TXT_PATH, do_process=False, constant_fields={"logID": "hi"}
        ))

        assert log.logID == "hi"

    def test_fromjson(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log1 = To.json(next(gen), DUMMY_JSON_PATH)
        log2 = next(From.json(parser, DUMMY_JSON_PATH, do_process=False))

        assert log1 == log2

        log = next(From.json(
            parser, DUMMY_JSON_PATH, do_process=False, constant_fields={"logID": "hi"}
        ))

        assert log.logID == "hi"

    def test_fromyaml(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log1 = To.yaml(next(gen), DUMMY_YAML_PATH)
        log2 = next(From.yaml(parser, DUMMY_YAML_PATH, do_process=False))

        assert log1 == log2

        log = next(From.yaml(
            parser, DUMMY_YAML_PATH, do_process=False, constant_fields={"logID": "hi"}
        ))

        assert log.logID == "hi"

    def test_frompolars(self):
        table = pl.DataFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "ParamList": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        gen = From.polars(DummyDetector(), df=table, do_process=False)

        parsed1 = next(gen)
        schema1 = sc.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "eventID": 0,
            "headerVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "eventID", "headerVariables"]:
            assert parsed1[field] == schema1[field], field
        assert parsed1["logID"] == "0"

        parsed2 = next(gen)
        schema2 = sc.ParserSchema({
            "log": "general kenobi",
            "variables": ["c", "d"],
            "template": "<*> kenobi",
            "eventID": 1,
            "headerVariables": {"Type": "B"}
        })
        for field in ["log", "variables", "template", "eventID", "headerVariables"]:
            assert parsed2[field] == schema2[field], field
        assert parsed2["logID"] == "1"

        gen = From.polars(
            DummyDetector(), df=table, do_process=False, constant_fields={"template": "hi"}
        )
        assert list(gen)[-1]["template"] == "hi"

    def test_frompolars_lazy(self):
        table = pl.LazyFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "ParamList": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        gen = From.polars(DummyDetector(), df=table, do_process=False)

        parsed1 = next(gen)
        schema1 = sc.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "eventID": 0,
            "headerVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "eventID", "headerVariables"]:
            assert parsed1[field] == schema1[field], field
        assert parsed1["logID"] == "0"

        parsed2 = next(gen)
        schema2 = sc.ParserSchema({
            "log": "general kenobi",
            "variables": ["c", "d"],
            "template": "<*> kenobi",
            "eventID": 1,
            "headerVariables": {"Type": "B"}
        })
        for field in ["log", "variables", "template", "eventID", "headerVariables"]:
            assert parsed2[field] == schema2[field], field
        assert parsed2["logID"] == "1"

        gen = From.polars(
            DummyDetector(), df=table, do_process=False, constant_fields={"template": "hi"}
        )
        parsed = next(gen)
        assert parsed["template"] == "hi"

    def test_frompolars_rename(self):
        table = pl.DataFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "Vars": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        renames = {
            "Content": "log", "Vars": "variables", "EventIDs": "eventID", "Templates": "template"
        }
        gen = From.polars(DummyDetector(), df=table, do_process=False, renames=renames)

        parsed1 = next(gen)
        schema1 = sc.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "eventID": 0,
            "headerVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "eventID", "headerVariables"]:
            assert parsed1[field] == schema1[field], field

    def test_frompolars_rename_vars(self):
        table = pl.LazyFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "Vars": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        renames = {
            "Content": "log", "Vars": "variables", "EventIDs": "eventID", "Templates": "template"
        }
        gen = From.polars(DummyDetector(), df=table, do_process=False, renames=renames)

        parsed1 = next(gen)
        schema1 = sc.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "eventID": 0,
            "headerVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "eventID", "headerVariables"]:
            assert parsed1[field] == schema1[field], field


# FromTo.<source>2<target>: the format names as they appear in the method names
EXTENSIONS = {"binary_file": "txt", "json": "json", "yaml": "yaml"}
FORMATS = list(EXTENSIONS)
TABLE = pl.DataFrame({
    "Type": ["A", "B"],
    "Content": ["hello there", "general kenobi"],
    "ParamList": [["a", "b"], ["c", "d"]],
    "Templates": ["hello <*>", "<*> kenobi"],
    "EventIDs": [0, 1]
})


def _written(fmt: str, path: str, schema: type = sc.ParserSchema) -> list[dict]:
    """The records in an output file, in order, as dicts."""
    with open(path) as f:
        if fmt == "binary_file":
            records = []
            for line in f:
                record = schema()
                record.deserialize(literal_eval(line.strip()))
                records.append(record.as_dict())
            return records
        data = json.load(f) if fmt == "json" else yaml.safe_load(f)
    return [data[key] for key in sorted(data, key=int)]


class TestCaseFromTo:
    @pytest.mark.parametrize("target", FORMATS)
    def test_log_to_file_writes_each_parsed_log(self, target):
        out_path = f"out.{EXTENSIONS[target]}"
        outputs = list(getattr(FromTo, f"log2{target}")(DummyParser(), AUDIT_TEMPLATES, out_path))

        with open(AUDIT_TEMPLATES) as f:
            assert [output["log"] for output in outputs] == [line.strip() for line in f]
        assert _written(target, out_path) == [output.as_dict() for output in outputs]

    @pytest.mark.parametrize("target", FORMATS)
    def test_log_to_file_writes_each_log_before_yielding_it(self, target):
        """A consumer that stops early still finds every log it received on
        disk."""
        out_path = f"out.{EXTENSIONS[target]}"
        gen = getattr(FromTo, f"log2{target}")(DummyParser(), AUDIT_TEMPLATES, out_path)

        received = [next(gen) for _ in range(5)]

        assert _written(target, out_path) == [log.as_dict() for log in received]

    @pytest.mark.parametrize("target", FORMATS)
    @pytest.mark.parametrize("source", FORMATS)
    def test_file_to_file_parses_each_record_and_writes_it(self, source, target):
        logs = list(From.log(DummyParser(), AUDIT_TEMPLATES, do_process=False))[:5]
        in_path, out_path = f"in.{EXTENSIONS[source]}", f"out.{EXTENSIONS[target]}"
        getattr(To, source)(logs, in_path)

        outputs = list(getattr(FromTo, f"{source}2{target}")(DummyParser(), in_path, out_path))

        assert all(isinstance(output, sc.ParserSchema) for output in outputs)
        assert [output["log"] for output in outputs] == [log["log"] for log in logs]
        assert _written(target, out_path) == [output.as_dict() for output in outputs]

    @pytest.mark.parametrize("target", FORMATS)
    def test_polars_to_file_writes_only_the_alerts(self, target):
        """DummyDetector alerts on every second record: here the row with
        logID 1."""
        out_path = f"out.{EXTENSIONS[target]}"
        outputs = list(getattr(FromTo, f"polars2{target}")(DummyDetector(), df=TABLE, out_path=out_path))

        assert outputs[0] is None
        written = _written(target, out_path, sc.DetectorSchema)
        assert [record["logIDs"] for record in written] == [["1"]]


class TestUseCase:
    # The idea of these tests is to check that they do not crash in normal use

    def test_case1(self):
        detector = DummyDetector()
        parser = DummyParser()

        alerts = []
        i = 0
        for parsed_log in From.log(parser, in_path=AUDIT_TEMPLATES):
            alerts.append(detector.process(parsed_log))
            if i >= 5:
                break
            i += 1

        assert len(alerts) == 6

    def test_case2(self):
        detector = DummyDetector()
        parser = DummyParser()

        parsed_logs = []
        i = 0
        for parsed_log in From.log(parser, in_path=AUDIT_TEMPLATES):
            parsed_logs.append(parsed_log)
            if i >= 5:
                break
            i += 1

        assert len(parsed_logs) == 6

        for parsed_log in parsed_logs:
            To.json(detector.process(parsed_log), out_path=DUMMY_JSON_PATH)

        assert os.path.exists(DUMMY_JSON_PATH)

    def test_case3(self):
        detector = DummyDetector()
        parser = DummyParser()

        parsed_logs = []
        i = 0
        for parsed_log in FromTo.log2json(parser, in_path=AUDIT_TEMPLATES, out_path=DUMMY_JSON_PATH):
            parsed_logs.append(parsed_log)
            if i >= 5:
                break
            i += 1

        assert len(parsed_logs) == 6

        for _ in FromTo.json2json(detector, in_path=DUMMY_JSON_PATH, out_path=DUMMY_JSON_PATH2):
            pass

        assert os.path.exists(DUMMY_JSON_PATH)
        assert os.path.exists(DUMMY_JSON_PATH2)

    def test_case4(self):
        matcher = dmp.match_tree.TreeMatcher(
            templates=dmp.types_.LogTemplates(["hello <*>"])
        )
        detector = DummyDetector()

        df = matcher(["hello there", "general kenobi"], get_var=True)
        for parsed_log in From.polars(detector, df=df):
            if parsed_log is not None:
                assert parsed_log["logIDs"] == ["1"]

        df = matcher(["hello there", "general kenobi"], get_var=False)
        for parsed_log in From.polars(detector, df=df):
            if parsed_log is not None:
                assert parsed_log["logIDs"] == ["1"]
