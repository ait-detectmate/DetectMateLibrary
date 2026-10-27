import math

from detectmatelibrary.detectors.new_value_detector import NewValueDetector, NewValueDetectorConfig
from detectmatelibrary.detectors.new_event_detector import NewEventDetector, NewEventDetectorConfig
from detectmatelibrary.detectors.bigram_frequency_detector import (
    BigramFrequencyDetector, BigramFrequencyDetectorConfig
)
from detectmatelibrary.common._core_op._train_buffer import TrainBuffer
from detectmatelibrary.common._core_op._fit_logic import FitLogicState
from detectmatelibrary.schemas import BaseSchema, LogSchema, ParserSchema
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL
from datetime import datetime


_PARSER_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>): <Content>",
            "time_format": None,
            "params": {
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True,
                "path_templates": AUDIT_TEMPLATES,
            },
        }
    }
}


def run_original(logs: list[BaseSchema], train_until):
    current_config = {
        "detectors": {
            "NewValueDetector": {
                "method_type": "new_value_detector",
                "auto_config": True,
                "data_use_configure": train_until,
                "data_use_training": train_until,
                "use_config_data_as_training": True,
                "params": {}
            },
            "NewEventDetector": {
                "method_type": "new_event_detector",
                "auto_config": True,
                "data_use_configure": train_until,
                "data_use_training": train_until,
                "use_config_data_as_training": True,
                "params": {}
            },
            "BigramFrequencyDetector": {
                "method_type": "bigram_frequency_detector",
                "auto_config": True,
                "data_use_configure": train_until,
                "data_use_training": train_until,
                "use_config_data_as_training": True,
                "params": {"skip_repetitions": True},
            }
        }
    }
    nvd = NewValueDetector(config=NewValueDetectorConfig.from_dict(current_config, method_id="NewValueDetector"), name="NewValueDetector")
    ned = NewEventDetector(config=NewEventDetectorConfig.from_dict(current_config, method_id="NewEventDetector"), name="NewEventDetector")
    bfd = BigramFrequencyDetector(config=BigramFrequencyDetectorConfig.from_dict(current_config, method_id="BigramFrequencyDetector"), name="BigramFrequencyDetector")
    detectors = [nvd, ned, bfd]

    start = datetime.now()
    for i in range(math.ceil(train_until / TRAIN_UNTIL)):
        for log in logs[:TRAIN_UNTIL]:
            if nvd.fitlogic.config_state.finished:
                break
            for detector in detectors:
                detector.process(log)
    end = datetime.now()

    detector_ids = [set() for _ in detectors]
    for log in logs[TRAIN_UNTIL:]:
        for i, detector in enumerate(detectors):
            if detector.process(log):
                detector_ids[i].add(log["logID"])
    detector_ids = [sorted(list(x)) for x in detector_ids]
    results = [[str(x) for x in range(1800, 2316) if x != 1863], ['1863'],
               ['1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867']]
    assert all([detector_ids[x] == results[x] for x in range(len(detector_ids))])
    print(f"Time needed for configuration and training with original setup {end - start} and train_until {train_until}.")


def run_new(logs: list[BaseSchema], train_until):
    # use_config_data_as_training to disable original TrainBuffer.
    current_config = {
        "detectors": {
            "NewValueDetector": {
                "method_type": "new_value_detector",
                "auto_config": True,
                "data_use_configure": train_until,
                "data_use_training": train_until,
                "use_config_data_as_training": False,
                "params": {}
            },
            "NewEventDetector": {
                "method_type": "new_event_detector",
                "auto_config": True,
                "data_use_configure": train_until,
                "data_use_training": train_until,
                "use_config_data_as_training": False,
                "params": {}
            },
            "BigramFrequencyDetector": {
                "method_type": "bigram_frequency_detector",
                "auto_config": True,
                "data_use_configure": train_until,
                "data_use_training": train_until,
                "use_config_data_as_training": False,
                "params": {"skip_repetitions": True},
            }
        }
    }
    nvd = NewValueDetector(config=NewValueDetectorConfig.from_dict(current_config, method_id="NewValueDetector"), name="NewValueDetector")
    ned = NewEventDetector(config=NewEventDetectorConfig.from_dict(current_config, method_id="NewEventDetector"), name="NewEventDetector")
    bfd = BigramFrequencyDetector(config=BigramFrequencyDetectorConfig.from_dict(current_config, method_id="BigramFrequencyDetector"), name="BigramFrequencyDetector")
    detectors = [nvd, ned, bfd]

    train_buffer = TrainBuffer(ParserSchema, name="TrainBuffer")

    start = datetime.now()
    # configuration
    for i in range(math.ceil(train_until / TRAIN_UNTIL)):
        for log in logs[:TRAIN_UNTIL]:
            for detector in detectors:
                detector.process(log)
            train_buffer.add(log)
            if len(train_buffer) == train_until:
                for detector in detectors:
                    assert detector.fitlogic.run() == FitLogicState.DO_TRAIN
                    assert detector.fitlogic.finish_config() is True
                    detector.set_configuration()
                break
    # training
    do_check = True
    for log in train_buffer:
        # detector.process is much slower and for fair comparison you just use the logs in train_buffer to train the detectors anyway.
        for detector in detectors:
            detector.train(log)
            detector.fitlogic.run()
        if do_check and len(train_buffer) == train_until - 1:  # one log was already consumed.
            assert nvd.fitlogic.config_state.finished
            assert ned.fitlogic.config_state.finished
            assert bfd.fitlogic.config_state.finished
            do_check = False
    end = datetime.now()

    do_check = True
    detector_ids = [set() for _ in detectors]
    for log in logs[TRAIN_UNTIL:]:
        for i, detector in enumerate(detectors):
            if detector.process(log):
                detector_ids[i].add(log["logID"])
        if do_check:
            assert nvd.fitlogic.train_state.finished
            assert ned.fitlogic.train_state.finished
            assert bfd.fitlogic.train_state.finished
            do_check = False
    detector_ids = [sorted(list(x)) for x in detector_ids]
    results = [[str(x) for x in range(1800, 2316) if x != 1863], ['1863'],
               ['1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867']]
    assert all([detector_ids[x] == results[x] for x in range(len(detector_ids))])
    print(f"Time needed for configuration and training with new setup {end - start} and train_until {train_until}.")


def main():
    # current setup uses internal TrainBuffer with default max_records=100_000.
    parser = MatcherParser(config=_PARSER_CONFIG)
    # logs are read from file and parsed at the same time. Do not want to rerun parsing.
    # logs are already deserialized Python objects. The training buffer must serialize the logs before storage, independently of the setup.
    logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True)) # about 2300 lines

    run_original(logs, 10_000)
    run_new(logs, 10_000)
    run_original(logs, 99_999)
    run_new(logs, 99_999)
    run_original(logs, 100_000)
    run_new(logs, 100_000)
    run_original(logs, 500_000)
    run_new(logs, 500_000)
    run_original(logs, 3_000_000)
    run_new(logs, 3_000_000)

if __name__ == "__main__":
    main()