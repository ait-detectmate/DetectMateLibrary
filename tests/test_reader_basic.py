from src.components.readers.log_file import LogFileConfig, LogFileReader


class TestCaseLogFileReader:
    def test_get_two_logs(self) -> None:
        reader = LogFileReader(
            config=LogFileConfig(**{"file": "tests/test_folder/logs.log"})
        )

        log1 = reader.process(as_bytes=False)
        assert isinstance(log1.log, str)
        assert log1.logID == 10

        log2 = reader.process(as_bytes=False)
        assert isinstance(log2.log, str)
        assert log2.logID == 11

        assert log1.log != log2.log

    def test_get_last_log(self) -> None:
        reader = LogFileReader(
            config=LogFileConfig(**{"file": "tests/test_folder/logs.log"})
        )

        for _ in range(10):
            log = reader.process()
        assert log is None

        # Check that will not crash after
        for _ in range(10):
            log = reader.process()
        assert log is None
