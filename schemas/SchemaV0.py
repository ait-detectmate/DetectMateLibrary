from BaseSchema import BaseSchema
from typing import List, Dict, Any

class LogSchemaV0(BaseSchema):
    LogID: int
    Log: str
    LogSource: str = None
    HostName: str = None

class ParserSchemaV0(BaseSchema):
    ParserType: str
    EventID: int
    Template: str
    Variables: list
    ParserID: int
    LogID: int
    Log: str
    LogFormatVariables: dict
    # optional fields
    # ReceivedTimestamp: int = None
    # ParsedTimestamp: int = None
    # Other: dict = None

class DetectorSchemaV0(BaseSchema):
    DetectorID: int
    DetectorType: str
    AlertID: int
    DetectionTimestamp: int
    LogID: List[int]
    Prediction_Label: bool
    Score: float
    ExtractedTimestamp: List[int]
    # optional fields
    # Description: str = None
    # ReceivedTimestamp: int = None
    # Other: dict = None