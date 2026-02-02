from detectmatelibrary.common.reader import CoreReaderConfig, CoreReader

import detectmatelibrary.schemas._op as op_schemas

import pydantic
import pytest


class MockupReader(CoreReader):
    def __init__(self, name: str, config: CoreReaderConfig | dict) -> None:
        super().__init__(name=name, config=config)

    def read(self, output_):
        output_.log = "Hello"
        return True


class MockupNoneReader(CoreReader):
    def __init__(self, name: str, config: CoreReaderConfig | dict) -> None:
        super().__init__(name=name, config=config)

    def read(self, output_):
        return False


class IncompleteMockupReader(CoreReader):
    def __init__(self, name: str, config: CoreReaderConfig | dict) -> None:
        super().__init__(name=name, config=config)

    def read(self, output_):
        return True


default_args = {
    "readers": {
        "TestReader": {
            "auto_config": True,
            "method_type": "core_reader"
        }
    }
}


class TestCoreDetector:
    def test_initialize_default(self) -> None:
        reader = MockupReader(name="TestReader", config=default_args)

        assert isinstance(reader, CoreReader)
        assert reader.name == "TestReader"
        assert isinstance(reader.config, CoreReaderConfig)

    def test_incorrect_config_type(self) -> None:
        invalid_args = {
            "readers": {
                "TestReader": {
                    "auto_config": True,
                    "method_type": "core_reader",
                    "invalid": "lololo"
                }
            }
        }
        with pytest.raises(pydantic.ValidationError):
            MockupReader(name="TestReader", config=invalid_args)

    def test_process_no_binary(self) -> None:
        config = CoreReaderConfig(**{"logSource": "TestSource", "hostname": "0.0.0.0"})

        reader = MockupReader(name="TestReader", config=config)
        output = reader.process(as_bytes=False)

        assert output.log == "Hello"
        assert output.logSource == "TestSource"
        assert output.hostname == "0.0.0.0"

    def test_process_binary(self) -> None:
        config = CoreReaderConfig(**{"logSource": "TestSource", "hostname": "0.0.0.0"})

        reader = MockupReader(name="TestReader", config=config)
        schema_id, output = op_schemas.deserialize(reader.process(as_bytes=True))

        assert schema_id == op_schemas.LOG_SCHEMA
        assert output.log == "Hello"
        assert output.logSource == "TestSource"
        assert output.hostname == "0.0.0.0"

    def test_process_logid_default(self) -> None:
        reader = MockupReader(name="TestReader", config=default_args)
        for i in range(10):
            assert reader.process(as_bytes=False).logID == str(10 + i)

    def test_process_None(self) -> None:
        reader = MockupNoneReader(name="TestReader", config=default_args)
        output = reader.process()

        assert output is None
