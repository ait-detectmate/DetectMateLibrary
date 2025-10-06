from src.components.common.reader import ReaderConfig, CoreReader
import src.schemas as schemas

import pydantic
import pytest


class MockupReader(CoreReader):
    def __init__(self, name: str, config: ReaderConfig | dict) -> None:
        super().__init__(name=name, config=config)

    def read(self, output_):
        output_.log = "Hello"
        return True


class MockupNoneReader(CoreReader):
    def __init__(self, name: str, config: ReaderConfig | dict) -> None:
        super().__init__(name=name, config=config)

    def read(self, output_):
        return False


class TestCoreDetector:
    def test_initialize_default(self) -> None:
        reader = MockupReader(name="TestReader", config={})

        assert isinstance(reader, CoreReader)
        assert reader.name == "TestReader"
        assert isinstance(reader.config, ReaderConfig)

    def test_incorrect_config_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockupReader(name="TestReader", config={"param1": "invalid_type", "param2": 0.5})

    def test_process_no_binary(self) -> None:
        config = ReaderConfig(**{"logSource": "TestSource", "hostname": "0.0.0.0"})

        reader = MockupReader(name="TestReader", config=config)
        output = reader.process(as_bytes=False)

        assert output.log == "Hello"
        assert output.logSource == "TestSource"
        assert output.hostname == "0.0.0.0"

    def test_process_binary(self) -> None:
        config = ReaderConfig(**{"logSource": "TestSource", "hostname": "0.0.0.0"})

        reader = MockupReader(name="TestReader", config=config)
        schema_id, output = schemas.deserialize(reader.process(as_bytes=True))

        assert schema_id == schemas.LOG_SCHEMA
        assert output.log == "Hello"
        assert output.logSource == "TestSource"
        assert output.hostname == "0.0.0.0"

    def test_process_logid_default(self) -> None:
        reader = MockupReader(name="TestReader", config={})
        for i in range(10):
            assert reader.process(as_bytes=False).logID == i

    def test_process_None(self) -> None:
        reader = MockupNoneReader(name="TestReader", config={})
        output = reader.process()

        assert output is None
