from detectmatelibrary.helper.from_to import From, To, FromTo
from detectmatelibrary._testutils.dummy_detector import DummyDetector
from detectmatelibrary._testutils.dummy_parser import DummyParser
from tests.test_data import AUDIT_TEMPLATES, DUMMY_TXT_PATH, DUMMY_TXT_PATH2, DUMMY_JSON_PATH, \
    DUMMY_JSON_PATH2, DUMMY_YAML_PATH, DUMMY_YAML_PATH2
import detectmatelibrary.schemas as schemas
import detectmateperformance as dmp
import polars as pl
import json
import yaml
import os


expected_log = "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> "
expected_log += "acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'"
log_path = "tests/test_data/audit_templates.txt"

binary_path = "tests/test_data/dummy.txt"
binary_path2 = "tests/test_data/dummy2.txt"
json_path = "tests/test_data/dummy.json"
json_path2 = "tests/test_data/dummy2.json"
yaml_path = "tests/test_data/dummy.yaml"
yaml_path2 = "tests/test_data/dummy2.yaml"


def remove_files(func):
    def remove():
        files = [
            DUMMY_TXT_PATH, DUMMY_TXT_PATH2, DUMMY_JSON_PATH, DUMMY_JSON_PATH2, DUMMY_YAML_PATH,
            DUMMY_YAML_PATH2
        ]
        for f in files:
            if os.path.exists(f):
                os.remove(f)

    def do(*args, **kwargs):
        remove()
        func(*args, **kwargs)
        remove()

    return do


class TestCaseTo:
    @remove_files
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

    @remove_files
    def test_tobinary_as_list(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)
        logs = [log.serialize() for log in gen]

        assert To.binary_file(logs, binary_path) == logs
        with open(binary_path, "r") as f:
            assert len(f.readlines()) == 9

    @remove_files
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

    @remove_files
    def test_tojson_list(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)
        logs = [log for log in gen]

        assert To.json(logs, json_path) == logs
        with open(json_path, "r") as f:
            assert len(json.load(f)) == 9

    @remove_files
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

    @remove_files
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
        assert isinstance(log, schemas.LogSchema)

    def test_fromlog(self):
        parser = DummyParser()

        log = next(From.log(parser, in_path=AUDIT_TEMPLATES, do_process=True))

        assert log.log == expected_log
        assert isinstance(log, schemas.ParserSchema)

    @remove_files
    def test_frombinary(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log1 = To.binary_file(next(gen), DUMMY_TXT_PATH)
        log2 = next(From.binary_file(parser, DUMMY_TXT_PATH, do_process=False))

        assert log1 == log2.serialize()

    @remove_files
    def test_fromjson(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log1 = To.json(next(gen), DUMMY_JSON_PATH)
        log2 = next(From.json(parser, DUMMY_JSON_PATH, do_process=False))

        assert log1 == log2

    @remove_files
    def test_fromyaml(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=AUDIT_TEMPLATES, do_process=False)

        log1 = To.yaml(next(gen), DUMMY_YAML_PATH)
        log2 = next(From.yaml(parser, DUMMY_YAML_PATH, do_process=False))

        assert log1 == log2

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
        schema1 = schemas.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "EventID": 0,
            "logFormatVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "EventID", "logFormatVariables"]:
            assert parsed1[field] == schema1[field], field
        assert parsed1["logID"] == "0"

        parsed2 = next(gen)
        schema2 = schemas.ParserSchema({
            "log": "general kenobi",
            "variables": ["c", "d"],
            "template": "<*> kenobi",
            "EventID": 1,
            "logFormatVariables": {"Type": "B"}
        })
        for field in ["log", "variables", "template", "EventID", "logFormatVariables"]:
            assert parsed2[field] == schema2[field], field
        assert parsed2["logID"] == "1"

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
        schema1 = schemas.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "EventID": 0,
            "logFormatVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "EventID", "logFormatVariables"]:
            assert parsed1[field] == schema1[field], field
        assert parsed1["logID"] == "0"

        parsed2 = next(gen)
        schema2 = schemas.ParserSchema({
            "log": "general kenobi",
            "variables": ["c", "d"],
            "template": "<*> kenobi",
            "EventID": 1,
            "logFormatVariables": {"Type": "B"}
        })
        for field in ["log", "variables", "template", "EventID", "logFormatVariables"]:
            assert parsed2[field] == schema2[field], field
        assert parsed2["logID"] == "1"

    def test_frompolars_rename(self):
        table = pl.DataFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "Vars": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        renames = {
            "Content": "log", "Vars": "variables", "EventIDs": "EventID", "Templates": "template"
        }
        gen = From.polars(DummyDetector(), df=table, do_process=False, renames=renames)

        parsed1 = next(gen)
        schema1 = schemas.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "EventID": 0,
            "logFormatVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "EventID", "logFormatVariables"]:
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
            "Content": "log", "Vars": "variables", "EventIDs": "EventID", "Templates": "template"
        }
        gen = From.polars(DummyDetector(), df=table, do_process=False, renames=renames)

        parsed1 = next(gen)
        schema1 = schemas.ParserSchema({
            "log": "hello there",
            "variables": ["a", "b"],
            "template": "hello <*>",
            "EventID": 0,
            "logFormatVariables": {"Type": "A"}
        })
        for field in ["log", "variables", "template", "EventID", "logFormatVariables"]:
            assert parsed1[field] == schema1[field], field


class TestCaseFromTo:
    @remove_files
    def test_log2binary(self):
        parser = DummyParser()
        gen = FromTo.log2binary_file(parser, AUDIT_TEMPLATES, DUMMY_TXT_PATH)

        values = []
        for _ in range(5):
            values.append(next(gen))

        with open(DUMMY_TXT_PATH) as f:
            assert 5 == len(f.readlines())

    @remove_files
    def test_log2json(self):
        parser = DummyParser()
        gen = FromTo.log2json(parser, AUDIT_TEMPLATES, DUMMY_JSON_PATH)

        values = []
        for _ in range(5):
            values.append(next(gen))

        with open(DUMMY_JSON_PATH) as f:
            assert 5 == len(json.load(f))

    @remove_files
    def test_log2yaml(self):
        parser = DummyParser()
        gen = FromTo.log2yaml(parser, AUDIT_TEMPLATES, DUMMY_YAML_PATH)

        values = []
        for _ in range(5):
            values.append(next(gen))

        with open(DUMMY_YAML_PATH) as f:
            assert 5 == len(yaml.safe_load(f))

    @remove_files
    def test_binary2binary(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.binary_file(next(gen), DUMMY_TXT_PATH))

        gen = FromTo.binary_file2binary_file(parser, DUMMY_TXT_PATH, DUMMY_TXT_PATH2)
        for _ in gen:
            pass

        with open(DUMMY_TXT_PATH2) as f:
            assert 5 == len(f.readlines())

    @remove_files
    def test_binary2json(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.binary_file(next(gen), DUMMY_TXT_PATH))

        gen = FromTo.binary_file2json(parser, DUMMY_TXT_PATH, DUMMY_JSON_PATH)
        for _ in gen:
            pass

        with open(DUMMY_JSON_PATH) as f:
            assert 5 == len(json.load(f))

    @remove_files
    def test_binary2yaml(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.binary_file(next(gen), DUMMY_TXT_PATH))

        gen = FromTo.binary_file2yaml(parser, DUMMY_TXT_PATH, DUMMY_YAML_PATH)
        for _ in gen:
            pass

        with open(DUMMY_YAML_PATH) as f:
            assert 5 == len(yaml.safe_load(f))

    @remove_files
    def test_json2binary(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.json(next(gen), DUMMY_JSON_PATH))

        gen = FromTo.json2binary_file(parser, DUMMY_JSON_PATH, DUMMY_TXT_PATH)
        for _ in gen:
            pass

        with open(DUMMY_TXT_PATH) as f:
            assert 5 == len(f.readlines())

    @remove_files
    def test_json2json(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.json(next(gen), DUMMY_JSON_PATH))

        gen = FromTo.json2json(parser, DUMMY_JSON_PATH, DUMMY_JSON_PATH2)
        for _ in gen:
            pass

        with open(DUMMY_JSON_PATH) as f:
            assert 5 == len(json.load(f))

    @remove_files
    def test_json2yaml(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.json(next(gen), DUMMY_JSON_PATH))

        gen = FromTo.json2yaml(parser, DUMMY_JSON_PATH, DUMMY_YAML_PATH)
        for _ in gen:
            pass

        with open(DUMMY_YAML_PATH) as f:
            assert 5 == len(yaml.safe_load(f))

    @remove_files
    def test_yaml2binary(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.yaml(next(gen), DUMMY_YAML_PATH))

        gen = FromTo.yaml2binary_file(parser, DUMMY_YAML_PATH, DUMMY_TXT_PATH)
        for _ in gen:
            pass

        with open(DUMMY_TXT_PATH) as f:
            assert 5 == len(f.readlines())

    @remove_files
    def test_yaml2json(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.yaml(next(gen), DUMMY_YAML_PATH))

        gen = FromTo.yaml2json(parser, DUMMY_YAML_PATH, DUMMY_JSON_PATH)
        for _ in gen:
            pass

        with open(DUMMY_JSON_PATH) as f:
            assert 5 == len(json.load(f))

    @remove_files
    def test_yaml2yaml(self):
        parser = DummyParser()
        gen = From.log(parser, AUDIT_TEMPLATES, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.yaml(next(gen), DUMMY_YAML_PATH))

        gen = FromTo.yaml2yaml(parser, DUMMY_YAML_PATH, DUMMY_YAML_PATH2)
        for _ in gen:
            pass

        with open(DUMMY_YAML_PATH2) as f:
            assert 5 == len(yaml.safe_load(f))

    @remove_files
    def test_polars2binary(self):
        detector = DummyDetector()
        table = pl.DataFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "ParamList": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        gen = FromTo.polars2binary_file(detector, df=table, out_path=DUMMY_TXT_PATH)
        for _ in gen:
            pass

        with open(DUMMY_TXT_PATH) as f:
            assert 1 == len(f.readlines())

    @remove_files
    def test_polars2json(self):
        detector = DummyDetector()
        table = pl.DataFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "ParamList": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        gen = FromTo.polars2json(detector, df=table, out_path=DUMMY_JSON_PATH)
        for _ in gen:
            pass

        with open(DUMMY_JSON_PATH) as f:
            assert 1 == len(json.load(f))

    @remove_files
    def test_polars2yaml(self):
        detector = DummyDetector()
        table = pl.DataFrame({
            "Type": ["A", "B"],
            "Content": ["hello there", "general kenobi"],
            "ParamList": [["a", "b"], ["c", "d"]],
            "Templates": ["hello <*>", "<*> kenobi"],
            "EventIDs": [0, 1]
        })
        gen = FromTo.polars2yaml(detector, df=table, out_path=DUMMY_YAML_PATH)
        for _ in gen:
            pass

        with open(DUMMY_YAML_PATH) as f:
            assert 1 == len(yaml.safe_load(f))


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

    @remove_files
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

    @remove_files
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

    @remove_files
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
