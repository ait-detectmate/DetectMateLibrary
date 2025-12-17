
from detectmatelibrary.common.output import CoreOutput, CoreOutputConfig, get_field, DetectorFieldNotFound
import detectmatelibrary.schemas as schemas

import pytest


class MockupConfig(CoreOutputConfig):
    pass


class MockupOutput(CoreOutput):
    def __init__(self, name: str, config: CoreOutputConfig) -> None:
        super().__init__(name=name, config=config)

    def do_output(self, input_, output_):
        pass


values = {
    "detectorID": "test id",
    "detectorType": "type test",
    "alertID": 0,
    "detectionTimestamp": 0,
    "logIDs": [0, 0, 0],
    "score": 0.0,
    "extractedTimestamps": [0, 0, 0],
    "description": "",
    "receivedTimestamp": 0,
}

values2 = {
    "detectorID": "test id2",
    "detectorType": "type test2",
    "alertID": 1,
    "detectionTimestamp": 1,
    "logIDs": [1, 1],
    "score": 1.0,
    "extractedTimestamps": [1, 1],
    "description": "",
    "receivedTimestamp": 1,
}


class TestGetField:
    def test_get_field_empty_schema(self):
        input_ = schemas.DetectorSchema()
        result = get_field(input_, "detectorID")
        assert result == [""]

    def test_get_field_missing_field(self):
        input_ = schemas.DetectorSchema()
        with pytest.raises(DetectorFieldNotFound):
            get_field(input_, "other_field")

    def test_get_field_single(self):
        input_ = schemas.DetectorSchema(values)
        result = get_field(input_, "score")
        assert result == [0.0]

    def test_get_field_list(self):
        input_ = [schemas.DetectorSchema(values), schemas.DetectorSchema(values2)]
        result = get_field(input_, "alertID")
        assert result == [0, 1]

    def test_get_list_of_list(self):
        input_ = [schemas.DetectorSchema(values), schemas.DetectorSchema(values2)]
        result = get_field(input_, "logIDs")
        assert result == [0, 0, 0, 1, 1]
