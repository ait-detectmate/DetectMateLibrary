
from detectmatelibrary.utils.aux import get_timestamp, time_test_mode

from datetime import datetime
from time import sleep

import pytest


class TestTimestamp:
    def test_test_mode(self) -> None:
        time_test_mode()
        assert get_timestamp() == 0

    def test_no_test_mode(self) -> None:
        time_test_mode(False)
        assert get_timestamp() != 0

    @pytest.mark.skip(reason="This test is too slow")
    def test_get_timestamp(self) -> None:
        time = get_timestamp()
        sleep(1)
        time2 = get_timestamp()

        time = datetime.fromtimestamp(time)
        time2 = datetime.fromtimestamp(time2)

        assert time.second != time2.second
