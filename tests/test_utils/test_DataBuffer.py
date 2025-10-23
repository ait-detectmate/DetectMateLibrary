from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer

import pytest


class TestDataBuffer:
    def test_no_buf_mode(self):
        results = []
        buf = DataBuffer(ArgsBuffer(mode="no_buf", process_function=results.append))
        buf.add(1)
        buf.add(2)
        assert results == [1, 2]

    def test_batch_mode(self):
        buf = DataBuffer(ArgsBuffer(mode="batch", process_function=sum, size=3))
        buf.add(1)
        buf.add(2)
        # Third add triggers processing
        result = buf.add(3)
        assert result == 6
        # Buffer should be empty after processing
        assert len(buf.buffer) == 0

    def test_batch_mode2(self):
        results = []
        buf = DataBuffer(ArgsBuffer(mode="batch", process_function=results.append, size=3))
        buf.add(1)
        assert results == []
        buf.add(1)
        assert results == []
        buf.add(1)
        assert results == [[1, 1, 1]]
        # Buffer should be empty after processing
        assert len(buf.buffer) == 0

    def test_window_mode(self):
        buf = DataBuffer(ArgsBuffer(mode="window", process_function=sum, size=2))
        assert buf.add(1) is None
        # Second add triggers processing
        assert buf.add(2) == 3
        # Third add slides window
        assert buf.add(5) == 7
        # Buffer should contain last two elements
        assert list(buf.buffer) == [2, 5]

    def test_flush_batch(self):
        results = []
        buf = DataBuffer(ArgsBuffer(
            mode="batch",
            process_function=lambda b: results.append(sum(b)),
            size=3
        ))
        buf.add(1)
        buf.add(2)
        buf.flush()
        assert results == [3]
        assert len(buf.buffer) == 0

    def test_flush_window(self):
        buf = DataBuffer(ArgsBuffer(mode="window", process_function=sum, size=2))
        buf.add(1)
        buf.add(2)
        buf.add(3)
        # flush should process but not clear buffer
        result = buf.flush()
        assert result == 5
        assert list(buf.buffer) == [2, 3]

    def test_invalid_mode(self):
        with pytest.raises(ValueError):
            DataBuffer(ArgsBuffer(mode="invalid", process_function=sum))

    def test_invalid_size_batch(self):
        with pytest.raises(ValueError):
            DataBuffer(ArgsBuffer(mode="batch", process_function=sum, size=1))

    def test_invalid_size_window(self):
        with pytest.raises(ValueError):
            DataBuffer(ArgsBuffer(mode="window", process_function=sum, size=None))

    def test_size_set_for_no_buf(self):
        with pytest.raises(ValueError):
            DataBuffer(ArgsBuffer(mode="no_buf", process_function=sum, size=2))
