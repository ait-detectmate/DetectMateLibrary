"""A detector's classification config reaches the stability trackers of its
stores."""
from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.base_detectors import VariableAutoConfigParams
from detectmatelibrary.utils.persistency.data_structures.trackers import (
    ClassificationMethods,
    EventStabilityTracker,
    SingleStabilityTracker,
)
import detectmatelibrary.schemas as sc
from detectmatelibrary.base_detectors import PersistConfig
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import (
    ComboAutoConfigParams,
    NewValueComboDetector,
    NewValueComboDetectorConfig,
)
from detectmatelibrary.utils.persistency import PersistencySaver


class TestConfigWiring:
    def test_block_reaches_per_variable_trackers(self):
        # CharsetDetector's `config` default is a shared mutable instance, so
        # pass explicit fresh configs (see test_time_dependent_stability.py).
        #
        # classification only shapes the configure-phase persistency: the
        # trained persistency is read by _check_variable, which never calls
        # classify(), so it never receives classification kwargs at all.
        default = CharsetDetector(config=CharsetDetectorConfig())
        assert default.persistency.event_struct.data_kwargs.get("classification") is None

        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.auto_config_params.classification = ClassificationMethods(
            index=True, slope_index=True
        )
        rebuilt = CharsetDetector(config=configured.config.to_dict(method_id="CharsetDetector"))
        block = rebuilt.auto_conf_persistency.event_struct.data_kwargs["classification"]
        assert ClassificationMethods(**block).enabled == ("index", "slope_index")

    def test_default_block_is_not_forwarded(self):
        """Forwarding the default would be noise; the tracker already has
        it."""
        default = CharsetDetector(config=CharsetDetectorConfig())
        assert "classification" not in (default.auto_conf_persistency.event_struct.data_kwargs or {})

    def test_config_field_round_trips(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.classification = ClassificationMethods(
            index=False, slope_time=True, decision="majority"
        )
        restored = type(detector.config).from_dict(
            detector.config.to_dict(method_id="CharsetDetector"), "CharsetDetector"
        )
        assert restored.auto_config_params.classification.enabled == ("slope_time",)
        assert restored.auto_config_params.classification.decision == "majority"

    def test_index_axis_methods_pull_in_no_timestamp_requirement(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.classification = ClassificationMethods(
            index=True, slope_index=True
        )
        rebuilt = CharsetDetector(config=detector.config.to_dict(method_id="CharsetDetector"))
        assert "classification" not in (rebuilt.persistency.event_struct.data_kwargs or {})

        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        tracker.add_value("a", timestamp=1.0)
        assert tracker.timestamps == []


def test_slope_threshold_reaches_the_classifier():
    """The threshold is configuration, not a constant buried in the
    classifier."""
    from detectmatelibrary.detectors.new_value_detector import (
        NewValueDetector,
        NewValueDetectorConfig,
    )

    detector = NewValueDetector(
        name="NewValueDetector",
        config=NewValueDetectorConfig(
            auto_config_params=VariableAutoConfigParams(
                classification=ClassificationMethods(
                    index=True, slope_index=True, slope_threshold=-0.25
                ),
            ),
        ),
    )
    persistency = detector.auto_conf_persistency
    tracker = EventStabilityTracker(**persistency.event_struct.data_kwargs)
    single = tracker.single_tracker_type()
    assert single.classification.enabled == ("index", "slope_index")
    assert single.stability_classifier.classification.slope_threshold == -0.25


def _parser_record(ts_value, event_id=1):
    return sc.ParserSchema({
        "parserType": "test",
        "eventID": event_id,
        "template": "test template",
        "variables": ["abc"],
        "logID": "1",
        "parsedLogID": "1",
        "parserID": "test_parser",
        "log": "test log message",
        "headerVariables": {"ts": ts_value},
    })


class TestSegmentationWithDetectorAddValueFn:
    """Segmentation="time" must work when a detector owns the value
    semantics."""

    def test_detector_backed_tracker_records_timestamps(self):
        tracker = SingleStabilityTracker(
            add_value_fn="CharsetDetector",
            classification=ClassificationMethods(index=False, time=True),
        )
        tracker.add_value("ab", timestamp=1.0)
        tracker.add_value("cd", timestamp=2.0)
        assert tracker.unique_set == {"a", "b", "c", "d"}
        assert tracker.timestamps == [1.0, 2.0]
        assert len(tracker.timestamps) == len(tracker.change_series)

    def test_value_range_skipped_value_keeps_alignment(self):
        """ValueRangeDetector returns early on non-numeric input without
        appending to change_series; timestamps must not drift."""
        tracker = SingleStabilityTracker(
            add_value_fn="ValueRangeDetector",
            classification=ClassificationMethods(index=False, time=True),
        )
        tracker.add_value("1", timestamp=1.0)
        tracker.add_value("not-a-number", timestamp=2.0)  # detector records nothing
        tracker.add_value("5", timestamp=3.0)
        assert len(tracker.change_series) == 2
        assert tracker.timestamps == [1.0, 3.0]

    def test_event_tracker_detector_backed_round_trip(self):
        event_tracker = EventStabilityTracker(
            add_value_fn="CharsetDetector",
            classification=ClassificationMethods(index=False, time=True),
        )
        event_tracker.add_data({"var1": "ab"}, timestamp=1.0)
        event_tracker.add_data({"var1": "cd"}, timestamp=2.0)
        restored = EventStabilityTracker.load(
            event_tracker.dump(),
            add_value_fn="CharsetDetector",
            classification={"index": False, "time": True},
        )
        single = restored.get_data()["var1"]
        assert single.unique_set == {"a", "b", "c", "d"}
        assert single.timestamps == [1.0, 2.0]


class TestClassificationConfigWiring:
    def test_flag_reaches_per_variable_trackers(self):
        # CharsetDetector's `config` parameter default is a single shared
        # CharsetDetectorConfig() instance (pre-existing mutable-default-arg
        # pitfall, unrelated to classification). Other tests in this
        # module mutate `detector.config.*` in place on a bare
        # CharsetDetector(), so we pass explicit fresh configs here to stay
        # isolated from that.
        # classification only shapes the configure-phase persistency: the
        # trained persistency is read by _check_variable, which never calls
        # classify(), so it never receives classification kwargs at all.
        detector = CharsetDetector(config=CharsetDetectorConfig())
        assert detector.persistency.event_struct.data_kwargs.get("classification") is None

        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.auto_config_params.classification = ClassificationMethods(
            index=False, time=True
        )
        rebuilt = CharsetDetector(config=configured.config.to_dict(method_id="CharsetDetector"))
        block = rebuilt.auto_conf_persistency.event_struct.data_kwargs["classification"]
        assert ClassificationMethods(**block).enabled == ("time",)

    def test_config_fields_round_trip(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.classification = ClassificationMethods(
            index=False, time=True
        )
        detector.config.auto_config_params.timestamp_variable = "ts"
        detector.config.auto_config_params.timestamp_format = "%y%m%d %H%M%S"
        restored = type(detector.config).from_dict(
            detector.config.to_dict(method_id="CharsetDetector"), "CharsetDetector"
        )
        assert restored.auto_config_params.classification.enabled == ("time",)
        assert restored.auto_config_params.timestamp_variable == "ts"
        assert restored.auto_config_params.timestamp_format == "%y%m%d %H%M%S"

    def test_configure_populates_timestamps_end_to_end(self):
        """The classification block reaches the configure-phase persistency's
        trackers end-to-end.

        This used to run through train()/.persistency, but the trained
        path no longer receives stability kwargs at all (see
        test_train_path_records_no_timestamps) -- configure()/
        .auto_conf_persistency is the phase these settings are for.
        """
        cfg = CharsetDetectorConfig(
            auto_config_params=VariableAutoConfigParams(
                classification=ClassificationMethods(index=False, time=True),
                timestamp_variable="ts",
                timestamp_format="%y%m%d %H%M%S",
            ),
        )
        detector = CharsetDetector(config=cfg, name="CharsetDetector")
        detector.configure(_parser_record("081109 203615"))
        detector.configure(_parser_record("081109 203645"))
        tracker = detector.auto_conf_persistency.get_events_data()[1].get_data()["var_0"]
        assert tracker.classification.enabled == ("time",)
        assert len(tracker.timestamps) == len(tracker.change_series) == 2
        assert tracker.timestamps[1] - tracker.timestamps[0] == 30.0


def test_train_path_records_no_timestamps():
    """Auto-config settings shape the configure-phase persistency only.

    Stability classification is never consulted at detect time, so the
    trained trackers would carry an unread timestamps list per variable.
    """
    from detectmatelibrary.base_detectors import VariableAutoConfigParams
    from detectmatelibrary.detectors.new_value_detector import (
        NewValueDetector,
        NewValueDetectorConfig,
    )

    detector = NewValueDetector(
        name="NewValueDetector",
        config=NewValueDetectorConfig(
            auto_config_params=VariableAutoConfigParams(
                classification=ClassificationMethods(index=False, time=True),
                timestamp_variable="ts",
            ),
        ),
    )
    records = [_parser_record(f"2026-08-04 10:{i:02d}:00") for i in range(20)]
    for record in records:
        detector.configure(record)
    detector.set_configuration()
    for record in records:
        detector.train(record)

    trained = detector.persistency.get_events_data()[1].get_data()
    assert trained, "expected the configure phase to select at least one variable"
    for tracker in trained.values():
        assert tracker.classification.enabled == ("index",)
        assert tracker.timestamps == []

    # the configure-phase persistency still gets them
    configured = detector.auto_conf_persistency.get_events_data()[1].get_data()
    assert any(t.classification.enabled == ("time",) for t in configured.values())


def test_persisted_state_omits_auto_config_params():
    """Persisted tracker state never carries auto_config_params: they are
    configure-phase-only inputs, and CharsetDetector's add_value closure
    (recovered from `detector_config` on reconstruction, see
    strip_auto_config_params in base_detectors/variable_detector.py) reads only
    operational fields, never auto_config_params.
    """
    cfg = CharsetDetectorConfig(
        auto_config_params=VariableAutoConfigParams(
            classification=ClassificationMethods(index=False, time=True),
            timestamp_variable="ts",
        ),
    )
    detector = CharsetDetector(config=cfg, name="CharsetDetector")
    for _ in range(5):
        detector.configure(_parser_record("2026-08-04 10:00:00"))
    detector.set_configuration()
    detector.train(_parser_record("2026-08-04 10:00:00"))

    trained = detector.persistency.get_events_data()[1].get_data()
    assert trained, "expected the configure phase to select at least one variable"
    for tracker in trained.values():
        state = tracker.to_state()
        entry = state["detector_config"]["detectors"]["CharsetDetector"]
        assert "auto_config_params" not in entry


class TestComboClassificationWiring:
    @staticmethod
    def _configured(classification: ClassificationMethods) -> NewValueComboDetector:
        cfg = NewValueComboDetectorConfig(
            auto_config_params=ComboAutoConfigParams(classification=classification),
        )
        detector = NewValueComboDetector(config=cfg, name="NewValueComboDetector")
        for i in range(10):
            detector.configure(sc.ParserSchema({
                "parserType": "test",
                "eventID": 1,
                "template": "Template 1",
                "variables": ["constant", f"varying_{i}", "another_constant"],
                "logID": str(i),
                "parsedLogID": str(i),
                "parserID": "test_parser",
                "log": "test log",
                "headerVariables": {},
            }))
        return detector

    def test_threshold_only_block_reaches_the_trackers(self):
        """The config layer forwards the block iff it differs from the default,
        so a block that differs only in its list must be forwarded."""
        detector = self._configured(ClassificationMethods(segment_thresholds=[0.5, 0.5]))
        trackers = detector.auto_conf_persistency.get_events_data()[1].get_data()
        assert trackers["var_1"].stability_classifier.segment_threshs == [0.5, 0.5]
        assert trackers["var_1"].stability_classifier.n_segments == 2

    def test_default_block_is_still_the_default_on_the_trackers(self):
        detector = self._configured(ClassificationMethods())
        trackers = detector.auto_conf_persistency.get_events_data()[1].get_data()
        assert trackers["var_1"].classification == ClassificationMethods()
        assert trackers["var_1"].stability_classifier.segment_threshs == [1.1, 0.3, 0.1, 0.01]


class TestTrackerReconstruction:
    def test_tracker_reconstruction_does_not_start_saver(self, monkeypatch):
        """A tracker reconstructs a throwaway detector by name to recover its
        add_value closure; that throwaway must not start a PersistencySaver
        even when the serialized detector_config carries a persist section (it
        would leak a saver thread per variable and clobber the real state
        file)."""
        starts: list = []
        monkeypatch.setattr(PersistencySaver, "start", lambda self: starts.append(self))

        detector_config = ValueRangeDetectorConfig(
            auto_config=False,
            persist=PersistConfig(path="memory://value_range_recon_no_leak/state"),
        ).to_dict(method_id="ValueRangeDetector")
        # precondition: the serialized config carries a persist section
        assert "persist" in detector_config["detectors"]["ValueRangeDetector"]

        tracker = SingleStabilityTracker(
            add_value_fn="ValueRangeDetector", detector_config=detector_config
        )
        # reconstruction recovered the range-semantics add_value closure...
        tracker.add_value(5)
        assert 5 in tracker.unique_set
        # ...but started NO saver (the throwaway instance must not persist)
        assert starts == []
