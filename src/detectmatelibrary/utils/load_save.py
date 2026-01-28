# type: ignore
from detectmatelibrary.common.core import CoreComponent
from detectmatelibrary.schemas import BaseSchema, LogSchema
from detectmatelibrary.utils.id_generator import SimpleIDGenerator

from kafka import KafkaConsumer, KafkaProducer
import pandas as pd
import os

from typing import Iterator


import warnings
warnings.warn("Warning!! this file is a prototype, it needs better testing and solve precommit issues!!!")


class From:
    @staticmethod
    def _yield(
        component: CoreComponent, in_: Iterator[BaseSchema], do_process: bool = True
    ) -> Iterator[BaseSchema]:
        for in_schema in in_:
            if do_process:
                yield component.process(in_schema)
            else:
                yield in_schema

    @staticmethod
    def log(
        component: CoreComponent, in_path: str, do_process: bool = True
    ) -> Iterator[BaseSchema]:
        def __generator():
            id_generator = SimpleIDGenerator(start_id=0)

            with open(in_path, "r") as f:
                for line in f:
                    yield LogSchema({
                        "log": line.strip(),
                        "logID": id_generator(),
                    })

        return From._yield(component, __generator(), do_process=do_process)

    @staticmethod
    def csv(
        component: CoreComponent, in_path: str, do_process: bool = True,
    ) -> Iterator[BaseSchema]:
        def __eval(x):
            try:
                value = eval(x)   # nosec CWE-78
                return value
            except Exception:
                return x

        def __generator():
            i = 0
            while True:
                row = pd.read_csv(in_path)
                i += 1
                if len(row) <= i:
                    break
                row = row.iloc[i]

                out_ = component.input_schema()
                for k, v in row.to_dict().items():
                    out_[k] = __eval(v) if k != "log" else v
                yield out_

        return From._yield(component, __generator(), do_process=do_process)

    @staticmethod
    def kafka(
        component: CoreComponent,
        in_topic: str,
        server: str,
        group_id: str,
        as_log: bool = True,
        do_process: bool = True,
    ) -> Iterator[BaseSchema]:

        consumer = KafkaConsumer(
            in_topic,
            bootstrap_servers=server,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            consumer_timeout_ms=1000
        )
        id_generator = SimpleIDGenerator(start_id=0)

        def __generator():
            while True:
                for msg in consumer:
                    if as_log:
                        yield LogSchema({
                            "log": msg.value.decode("utf-8"),
                            "logID": id_generator(),
                        })
                    else:
                        schema = component.input_schema()
                        schema.deserialize(msg.value)
                        yield schema

        return From._yield(component, __generator(), do_process=do_process)


class From2To:
    @staticmethod
    def __2csv(
        in_: Iterator[BaseSchema], out_path: str
    ) -> Iterator[pd.DataFrame]:
        for out_ in in_:
            if out_ is None:
                yield None
                continue

            if os.path.exists(out_path):
                (table := pd.concat([
                    pd.read_csv(out_path), pd.DataFrame([out_.as_dict()])
                ])).to_csv(out_path, index=False)
            else:
                (table := pd.DataFrame([out_.as_dict()])).to_csv(out_path, index=False)

            yield table

    @staticmethod
    def __2kafka(
        in_: Iterator[BaseSchema], server: str, out_topic: str,
    ) -> Iterator[BaseSchema]:

        producer = KafkaProducer(
            bootstrap_servers=server,
            acks="all",
            retries=5,
        )
        for msg in in_:

            future = producer.send(out_topic, msg.serialize())
            try:
                future.get(timeout=10)
            except Exception as e:
                print("send failed:", e)

    @staticmethod
    def log2csv(
        component: CoreComponent, in_path: str, out_path: str, do_process: bool = True
    ) -> Iterator[pd.DataFrame]:

        return From2To.__2csv(
            in_=From.log(component=component, in_path=in_path, do_process=do_process),
            out_path=out_path,
        )

    @staticmethod
    def csv2csv(
        component: CoreComponent, in_path: str, out_path: str, do_process: bool = True
    ) -> Iterator[pd.DataFrame]:

        return From2To.__2csv(
            in_=From.csv(component=component, in_path=in_path, do_process=do_process),
            out_path=out_path,
        )

    @staticmethod
    def kafka2csv(
        component: CoreComponent,
        in_topic: str,
        server: str,
        group_id: str,
        out_path: str,
        as_log:
        bool = True,
        do_process: bool = True
    ) -> Iterator[pd.DataFrame]:

        return From2To.__2csv(
            in_=From.kafka(
                component=component,
                as_log=as_log,
                do_process=do_process,
                in_topic=in_topic,
                server=server,
                group_id=group_id,
            ),
            out_path=out_path,
        )

    @staticmethod
    def log2kafka(
        component: CoreComponent,
        in_path: str,
        out_topic: str,
        server: str,
        do_process: bool = True,
    ) -> Iterator[BaseSchema]:

        return From2To.__2kafka(
            in_=From.log(component=component, in_path=in_path, do_process=do_process),
            out_topic=out_topic,
            server=server,
        )

    @staticmethod
    def csv2kafka(
        component: CoreComponent,
        in_path: str,
        out_topic: str,
        server: str,
        do_process: bool = True,
    ) -> Iterator[pd.DataFrame]:

        return From2To.__2kafka(
            in_=From.csv(component=component, in_path=in_path, do_process=do_process),
            out_topic=out_topic,
            server=server,
        )

    @staticmethod
    def kafka2kafka(
        component: CoreComponent,
        in_topic: str,
        out_topic: str,
        server: str,
        groupd_id: str,
        as_log: bool = True,
        do_process: bool = True,
    ) -> Iterator[pd.DataFrame]:

        return From2To.__2kafka(
            in_=From.kafka(
                component=component,
                in_topic=in_topic,
                group_id=groupd_id,
                server=server,
                as_log=as_log,
                do_process=do_process,
            ),
            server=server,
            out_topic=out_topic,
        )
