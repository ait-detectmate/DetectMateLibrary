from detectmatelibrary.schemas import BaseSchema


from typing import Tuple


class SchemaPipeline:
    @staticmethod
    def preprocess(
        input_: BaseSchema, data: BaseSchema | bytes
    ) -> Tuple[bool, BaseSchema]:

        is_byte = False
        if isinstance(data, bytes):
            is_byte = True
            input_.deserialize(data)
            data = input_.copy()
        else:
            data = data.copy()

        return is_byte, data

    @staticmethod
    def postprocess(
        data: BaseSchema, is_byte: bool
    ) -> BaseSchema | bytes:

        return data if not is_byte else data.serialize()
