import detectmatelibrary.schemas as schemas

from typing import Any
import pandas as pd


class DataNormalizer:
    """A class for normalizing input data.

    Shall be able to convert DataFrames, Dicts, Lists to Schemas.
    """

    def __init__(
        self,
        data: pd.DataFrame | dict[str, Any] | list[Any],
        input_schema: schemas.BaseSchema,
        output_schema: schemas.BaseSchema
    ) -> None:
        self.data = data
        self.input_schema = input_schema
        self.output_schema = output_schema

    def normalize(self) -> pd.DataFrame:
        if isinstance(self.data, pd.DataFrame):
            return self.data
        elif isinstance(self.data, dict):
            return pd.DataFrame.from_records([self.data])
        elif isinstance(self.data, list):
            return pd.DataFrame.from_records(self.data)
        else:
            raise ValueError("Unsupported data type")
