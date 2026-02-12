from detectmatelibrary.utils.from_to import From, To, FromTo

from detectmatelibrary.parsers.dummy_parser import DummyParser

import detectmatelibrary.schemas as schemas

import json
import os


expected_log = "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> "
expected_log += "acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'"
log_path = "tests/test_folder/audit_templates.txt"

binary_path = "tests/test_folder/dummy.txt"
binary_path2 = "tests/test_folder/dummy2.txt"
json_path = "tests/test_folder/dummy.json"
json_path2 = "tests/test_folder/dummy2.json"


def remove_files(func):
    def remove():
        files = [binary_path, binary_path2, json_path, json_path2]
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
        gen = From.log(parser, in_path=log_path, do_process=False)

        log = next(gen)
        assert To.binary_file(log, binary_path) == log.serialize()

        log = next(gen)
        assert To.binary_file(log.serialize(), binary_path) == log.serialize()

        assert To.binary_file(None, binary_path) is None

        with open(binary_path, "r") as f:
            assert len(f.readlines()) == 2

    @remove_files
    def test_tojson(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)

        log = next(gen)
        assert To.json(log, json_path) == log

        log = next(gen)
        assert To.json(log, json_path) == log

        assert To.json(None, json_path) is None

        with open(json_path, "r") as f:
            assert len(json.load(f)) == 2


class TestCaseFrom:
    def test_fromlog_no_process(self):
        parser = DummyParser()

        log = next(From.log(parser, in_path=log_path, do_process=False))

        assert log.log == expected_log
        assert isinstance(log, schemas.LogSchema)

    def test_fromlog(self):
        parser = DummyParser()

        log = next(From.log(parser, in_path=log_path, do_process=True))

        assert log.log == expected_log
        assert isinstance(log, schemas.ParserSchema)

    @remove_files
    def test_frombinary(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)

        log1 = To.binary_file(next(gen), binary_path)
        log2 = next(From.binary_file(parser, binary_path, do_process=False))

        assert log1 == log2.serialize()

    @remove_files
    def test_fromjson(self):
        parser = DummyParser()
        gen = From.log(parser, in_path=log_path, do_process=False)

        log1 = To.json(next(gen), json_path)
        log2 = next(From.json(parser, json_path, do_process=False))

        assert log1 == log2


class TestCaseFromTo:
    @remove_files
    def test_log2binary(self):
        parser = DummyParser()
        gen = FromTo.log2binary_file(parser, log_path, binary_path)

        values = []
        for _ in range(5):
            values.append(next(gen))

        with open(binary_path) as f:
            assert 5 == len(f.readlines())

    @remove_files
    def test_log2json(self):
        parser = DummyParser()
        gen = FromTo.log2bjson(parser, log_path, json_path)

        values = []
        for _ in range(5):
            values.append(next(gen))

        with open(json_path) as f:
            assert 5 == len(json.load(f))

    @remove_files
    def test_binary2binary(self):
        parser = DummyParser()
        gen = From.log(parser, log_path, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.binary_file(next(gen), binary_path))

        gen = FromTo.binary_file2binary_file(parser, binary_path, binary_path2)
        for _ in gen:
            pass

        with open(binary_path2) as f:
            assert 5 == len(f.readlines())

    @remove_files
    def test_binary2json(self):
        parser = DummyParser()
        gen = From.log(parser, log_path, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.binary_file(next(gen), binary_path))

        gen = FromTo.binary_file2json(parser, binary_path, json_path)
        for _ in gen:
            pass

        with open(json_path) as f:
            assert 5 == len(json.load(f))

    @remove_files
    def test_json2binary(self):
        parser = DummyParser()
        gen = From.log(parser, log_path, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.json(next(gen), json_path))

        gen = FromTo.json2binary_file(parser, json_path, binary_path)
        for _ in gen:
            pass

        with open(binary_path) as f:
            assert 5 == len(f.readlines())

    @remove_files
    def test_json2json(self):
        parser = DummyParser()
        gen = From.log(parser, log_path, do_process=False)
        values = []
        for _ in range(5):
            values.append(To.json(next(gen), json_path))

        gen = FromTo.json2json(parser, json_path, json_path2)
        for _ in gen:
            pass

        with open(json_path) as f:
            assert 5 == len(json.load(f))
