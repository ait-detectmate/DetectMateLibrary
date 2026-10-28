import logging

from detectmatelibrary.base_detectors import (
    SequenceAutoConfigParams,
    TrackerDetectorConfig,
    feed_candidate_windows,
    warn_if_never_configured,
)


def test_feed_candidate_windows_returns_only_full_windows():
    windows: dict = {}
    params = SequenceAutoConfigParams(min_window_size=2, max_window_size=3)
    assert feed_candidate_windows(windows, "a", params) == []
    full = feed_candidate_windows(windows, "b", params)
    assert [(n, list(w)) for n, w in full] == [(2, ["a", "b"])]
    full = feed_candidate_windows(windows, "c", params)
    assert [(n, list(w)) for n, w in full] == [(2, ["b", "c"]), (3, ["a", "b", "c"])]


def test_feed_candidate_windows_follows_a_changed_range():
    windows: dict = {}
    params = SequenceAutoConfigParams(min_window_size=2, max_window_size=3)
    params.min_window_size, params.max_window_size = 4, 5
    feed_candidate_windows(windows, "a", params)
    assert set(windows) == {4, 5}


def test_warn_if_never_configured(caplog):
    with caplog.at_level(logging.WARNING):
        assert warn_if_never_configured("D", TrackerDetectorConfig(), False) is True
        assert warn_if_never_configured("D", TrackerDetectorConfig(), True) is True
        assert warn_if_never_configured("D", TrackerDetectorConfig(data_use_configure=5), False) is False
        assert warn_if_never_configured("D", TrackerDetectorConfig(auto_config=False), False) is False
    assert sum("data_use_configure is not set" in r.message for r in caplog.records) == 1
