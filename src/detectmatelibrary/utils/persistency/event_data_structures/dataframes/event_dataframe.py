from typing import Any, Dict, List

from dataclasses import dataclass, field

import pandas as pd

from ..base import EventDataStructure


# -------- Pandas backend --------

@dataclass
class EventDataFrame(EventDataStructure):
    """
    Pandas DataFrame backend:
    - Ingest appends data (expensive)
    - Retention is not handled (can be extended)
    - DataFrame is always materialized
    """
    data: pd.DataFrame = field(default_factory=pd.DataFrame)

    def add_data(self, data: pd.DataFrame) -> None:
        if len(self.data) > 0:
            self.data = pd.concat([self.data, data], ignore_index=True)
        else:
            self.data = data

    def get_data(self) -> pd.DataFrame:
        return self.data

    def get_variables(self) -> List[str]:
        return list(self.data.columns)

    def to_data(self, raw_data: Dict[int | str, Any]) -> pd.DataFrame:
        data = {key: [value] for key, value in raw_data.items()}
        return pd.DataFrame(data)

    def __repr__(self) -> str:
        return f"EventDataFrame(df=..., rows={len(self.data)}, variables={self.get_variables()})"
