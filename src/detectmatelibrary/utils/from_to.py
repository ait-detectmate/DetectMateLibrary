from detectmatelibrary.common.core import CoreComponent
from detectmatelibrary.schemas import BaseSchema, LogSchema
from detectmatelibrary.utils.id_generator import SimpleIDGenerator

from ast import literal_eval
import os

from typing import Iterator
import json


class To:
    @staticmethod
    def binary_file(out_: BaseSchema | bytes | None, out_path: str) -> bytes | None:
        if out_ is None:
            return None
        elif isinstance(out_, BaseSchema):
            out_ = out_.serialize()

        data = [str(out_) + "\n"]
        if os.path.exists(out_path):
            with open(out_path, "r") as f:
                data = f.readlines() + data

        with open(out_path, "w") as f:
            f.writelines(data)

        return out_

    @staticmethod
    def json(out_: BaseSchema | None, out_path: str) -> BaseSchema | None:
        if out_ is None:
            return None

        data = {}
        if os.path.exists(out_path):
            with open(out_path) as f:
                data = json.load(f)

        data[len(data)] = out_.as_dict()
        with open(out_path, "w") as f:
            obj = literal_eval(str(data))
            json.dump(obj, f, indent=4, ensure_ascii=False)

        return out_


class From:
    @staticmethod
    def _yield(
        component: CoreComponent, in_: Iterator[BaseSchema], do_process: bool = True
    ) -> Iterator[BaseSchema]:
        for in_schema in in_:
            if do_process:
                yield component.process(in_schema)  # type: ignore
            else:
                yield in_schema

    @staticmethod
    def log(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        def __generator():  # type: ignore
            id_generator = SimpleIDGenerator(start_id=0)

            with open(in_path, "r") as f:
                for line in f:
                    yield LogSchema({
                        "log": line.strip(),
                        "logID": str(id_generator()),
                    })

        return From._yield(component, __generator(), do_process=do_process)  # type: ignore

    @staticmethod
    def binary_file(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        def __generator():  # type: ignore
            with open(in_path, "r") as f:
                for line in f:
                    schema = component.input_schema()
                    schema.deserialize(literal_eval(line.strip()))
                    yield schema

        return From._yield(component, __generator(), do_process=do_process)  # type: ignore

    @staticmethod
    def json(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        def __generator():  # type: ignore
            with open(in_path, "r") as f:
                data = json.load(f)
            for i in range(len(data)):
                schema = component.input_schema(data[str(i)])
                yield schema

        return From._yield(component, __generator(), do_process=do_process)  # type: ignore


class FromTo:
    @staticmethod
    def log2binary_file(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        gen = From.log(component, in_path=in_path, do_process=True)

        for log in gen:
            To.binary_file(log, out_path=out_path)
            yield log

    @staticmethod
    def log2bjson(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        gen = From.log(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.json(log, out_path=out_path)  # type: ignore

    @staticmethod
    def binary_file2binary_file(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:

        gen = From.binary_file(component, in_path=in_path, do_process=True)

        for log in gen:
            To.binary_file(log, out_path=out_path)
            yield log

    @staticmethod
    def binary_file2json(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.binary_file(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.json(log, out_path=out_path)  # type: ignore

    @staticmethod
    def json2binary_file(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.json(component, in_path=in_path, do_process=True)

        for log in gen:
            To.binary_file(log, out_path=out_path)
            yield log

    @staticmethod
    def json2json(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.json(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.json(log, out_path=out_path)  # type: ignore
