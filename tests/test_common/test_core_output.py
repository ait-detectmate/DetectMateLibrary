
from detectmatelibrary.common.output import CoreOutput, CoreOutputConfig, get_field, DetectorFieldNotFound
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.aux import time_test_mode
import detectmatelibrary.schemas as schemas

import pytest


class MockupConfig(CoreOutputConfig):
    pass


class MockupOutput(CoreOutput):
    def __init__(self, name: str, config: CoreOutputConfig) -> None:
        super().__init__(
            name=name, config=config, buffer_mode=BufferMode.WINDOW, buffer_size=2
        )

    def do_output(self, input_, output_):
        output_["description"] = "hi"
        output_["alertsObtain"] = {"ciao": "bella"}


values = {
    "detectorID": "test id",
    "detectorType": "type test",
    "alertID": "0",
    "detectionTimestamp": 0,
    "logIDs": ["0", "0", "0"],
    "score": 0.0,
    "extractedTimestamps": [0, 0, 0],
    "description": "",
    "receivedTimestamp": 0,
}

values2 = {
    "detectorID": "test id2",
    "detectorType": "type test2",
    "alertID": "1",
    "detectionTimestamp": 1,
    "logIDs": ["1", "1"],
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
        assert result == ["0", "1"]

    def test_get_list_of_list(self):
        input_ = [schemas.DetectorSchema(values), schemas.DetectorSchema(values2)]
        result = get_field(input_, "logIDs")
        assert result == ["0", "0", "0", "1", "1"]


time_test_mode()


class TestCoreOutput:
    def test_initialization(self):
        config = MockupConfig()
        output = MockupOutput(name="TestOutput", config=config)

        assert output.name == "TestOutput"
        assert output.config == config
        assert output.input_schema == schemas.DetectorSchema
        assert output.output_schema == schemas.OutputSchema

    def test_run(self):
        config = MockupConfig()
        output = MockupOutput(name="TestOutput", config=config)

        input_ = [
            schemas.DetectorSchema(values),
            schemas.DetectorSchema(values2)
        ]
        output_ = schemas.OutputSchema()

        output.run(input_=input_, output_=output_)

        assert output_.detectorIDs == ["test id", "test id2"]
        assert output_.detectorTypes == ["type test", "type test2"]
        assert output_.alertIDs == ["0", "1"]
        assert output_.logIDs == ["0", "0", "0", "1", "1"]
        assert output_.extractedTimestamps == [0, 0, 0, 1, 1]
        assert output_.outputTimestamp == 0
        assert output_.description == "hi"
        assert output_.alertsObtain == {"ciao": "bella"}

    def test_process(self):
        config = MockupConfig()
        output = MockupOutput(name="TestOutput", config=config)

        assert output.process(schemas.DetectorSchema(values)) is None

        result = output.process(schemas.DetectorSchema(values2))

        assert result.detectorIDs == ["test id", "test id2"]
        assert result.detectorTypes == ["type test", "type test2"]
        assert result.alertIDs == ["0", "1"]
        assert result.logIDs == ["0", "0", "0", "1", "1"]
        assert result.extractedTimestamps == [0, 0, 0, 1, 1]
        assert result.description == "hi"
        assert result.alertsObtain == {"ciao": "bella"}
        assert result.outputTimestamp == 0
