from detectmatelibrary.common.core import CoreComponent
from detectmatelibrary.schemas import BaseSchema, LogSchema
from detectmatelibrary.utils.id_generator import SimpleIDGenerator

from ast import literal_eval
import os

from polars import DataFrame
from typing import overload
from typing import Iterator
import yaml
import json


def normalize_output(func):  # type: ignore
    def norm(*args, **kwargs):  # type: ignore
        if isinstance(args[0], list):
            return func(*args, **kwargs)
        else:
            aux = func(*args, **kwargs)
            return aux[0] if aux is not None else None
    return norm


class To:
    @staticmethod
    @overload
    def binary_file(out_: BaseSchema | bytes | None, out_path: str) -> bytes | None:
        ...

    @staticmethod
    @overload
    def binary_file(out_: list[BaseSchema] | list[bytes], out_path: str) -> list[bytes]:
        ...

    @staticmethod
    @normalize_output  # type: ignore
    def binary_file(
        out_: BaseSchema | bytes | None | list[BaseSchema] | list[bytes], out_path: str
    ) -> bytes | None | list[bytes]:

        if out_ is None:
            return None

        elif isinstance(out_, BaseSchema):
            out_ = [out_.serialize()]
        elif isinstance(out_, list) and isinstance(out_[0], BaseSchema):
            out_ = [o_.serialize() for o_ in out_]  # type: ignore
        elif isinstance(out_, bytes):
            out_ = [out_]

        data = [str(o_) + "\n" for o_ in out_]
        if os.path.exists(out_path):
            with open(out_path, "r") as f:
                data = f.readlines() + data

        with open(out_path, "w") as f:
            f.writelines(data)

        return out_   # type: ignore

    @overload
    @staticmethod
    def json(out_: BaseSchema | None, out_path: str) -> BaseSchema | None:
        ...

    @overload
    @staticmethod
    def json(out_: list[BaseSchema], out_path: str) -> list[BaseSchema]:
        ...

    @staticmethod
    @normalize_output  # type: ignore
    def json(
        out_: BaseSchema | None | list[BaseSchema], out_path: str
    ) -> BaseSchema | None | list[BaseSchema]:

        if out_ is None:
            return None
        if isinstance(out_, BaseSchema):
            out_ = [out_]

        data = {}
        if os.path.exists(out_path):
            with open(out_path) as f:
                data = json.load(f)

        n = len(data)
        for i, o_ in enumerate(out_):
            data[n + i] = o_.as_dict()

        with open(out_path, "w") as f:
            obj = literal_eval(str(data))
            json.dump(obj, f, indent=4, ensure_ascii=False)

        return out_

    @staticmethod
    @overload
    def yaml(out_: BaseSchema | None, out_path: str) -> BaseSchema | None:
        ...

    @staticmethod
    @overload
    def yaml(out_: list[BaseSchema], out_path: str) -> list[BaseSchema] | None:
        ...

    @staticmethod
    @normalize_output  # type: ignore
    def yaml(
        out_: BaseSchema | None | list[BaseSchema], out_path: str
    ) -> BaseSchema | None | list[BaseSchema]:

        if out_ is None:
            return None
        if isinstance(out_, BaseSchema):
            out_ = [out_]

        data = {}
        if os.path.exists(out_path):
            with open(out_path) as f:
                data = yaml.safe_load(f)

        n = len(data)
        for i, o_ in enumerate(out_):
            data[n + i] = o_.as_dict()

        with open(out_path, "w") as f:
            obj = literal_eval(str(data))
            yaml.safe_dump(obj, f, indent=4, default_flow_style=False)

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

    @staticmethod
    def yaml(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        def __generator():  # type: ignore
            with open(in_path, "r") as f:
                data = yaml.safe_load(f)
            for i in range(len(data)):
                schema = component.input_schema(data[i])
                yield schema

        return From._yield(component, __generator(), do_process=do_process)  # type: ignore

    @staticmethod
    def polars(
        component: CoreComponent,
        df: DataFrame,
        do_process: bool = True,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        def __generator():  # type: ignore
            for i in range(len(df)):
                data = df.row(i, named=True)
                if len(df_vars) > 0:
                    data["logFormatVariables"] = df_vars.row(i, named=True)
                data["logID"] = str(i)
                schema = component.input_schema(data)
                yield schema

        renames = {
            "Content": "log", "ParamList": "variables", "EventIDs": "EventID", "Templates": "template"
        } if renames is None else renames
        if "ParamList" not in df.columns and "ParamList" in renames:
            del renames["ParamList"]

        columns = list(renames.values())
        df = df.rename(renames)
        format_vars = [colum for colum in df.columns if colum not in columns]
        df_vars, df = df[format_vars], df[columns]

        return From._yield(component, __generator(), do_process=do_process)  # type: ignore


class FromTo:
    @staticmethod
    def log2binary_file(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        gen = From.log(component, in_path=in_path, do_process=True)

        for log in gen:
            To.binary_file(log, out_path=out_path)
            yield log

    @staticmethod
    def log2json(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        gen = From.log(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.json(log, out_path=out_path)  # type: ignore

    @staticmethod
    def log2yaml(component: CoreComponent, in_path: str, out_path: str) -> Iterator[BaseSchema]:
        gen = From.log(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.yaml(log, out_path=out_path)  # type: ignore

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
    def binary_file2yaml(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.binary_file(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.yaml(log, out_path=out_path)  # type: ignore

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

    @staticmethod
    def json2yaml(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.json(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.yaml(log, out_path=out_path)  # type: ignore

    @staticmethod
    def yaml2binary_file(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.yaml(component, in_path=in_path, do_process=True)

        for log in gen:
            To.binary_file(log, out_path=out_path)
            yield log

    @staticmethod
    def yaml2json(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.yaml(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.json(log, out_path=out_path)  # type: ignore

    @staticmethod
    def yaml2yaml(
        component: CoreComponent, in_path: str, out_path: str
    ) -> Iterator[BaseSchema]:
        gen = From.yaml(component, in_path=in_path, do_process=True)

        for log in gen:
            yield To.yaml(log, out_path=out_path)  # type: ignore

    @staticmethod
    def polars2binary_file(
        component: CoreComponent,
        df: DataFrame,
        out_path: str,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        gen = From.polars(component, df=df, renames=renames, do_process=True)

        for log in gen:
            yield To.binary_file(log, out_path=out_path)  # type: ignore

    @staticmethod
    def polars2json(
        component: CoreComponent,
        df: DataFrame,
        out_path: str,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        gen = From.polars(component, df=df, renames=renames, do_process=True)

        for log in gen:
            yield To.json(log, out_path=out_path)  # type: ignore

    @staticmethod
    def polars2yaml(
        component: CoreComponent,
        df: DataFrame,
        out_path: str,
        renames: dict[str, str] | None = None
    ) -> Iterator[BaseSchema]:
        gen = From.polars(component, df=df, renames=renames, do_process=True)

        for log in gen:
            yield To.yaml(log, out_path=out_path)  # type: ignore
