from detectmatelibrary.detectors.NewValueDetector import NewValueDetector, NewValueDetectorConfig
from detectmatelibrary.common.config.detector import DetectorInstance, DetectorVariable
from detectmatelibrary.common.detector import CoreDetectorConfig
import detectmatelibrary.schemas as schemas


config = CoreDetectorConfig(
    detectorID="random_detector",
    detectorType="randomDetector",
    auto_config=False,
    instances=[
        DetectorInstance(
            id="random_detector_1",
            event=0,
            variables=[
                DetectorVariable(pos="level", params=NewValueDetectorConfig(threshold=0.8))
            ],
        ),
        DetectorInstance(
            id="random_detector_2",
            event="all",
            variables=[
                DetectorVariable(pos="level", params=NewValueDetectorConfig(threshold=0.8))
            ],
        ),
    ]
)
output = schemas.initialize(
    schema_id=schemas.DETECTOR_SCHEMA,
    **{
        "__version__": "1.0.0",
        "detectorID": config.detectorID,
        "detectorType": config.detectorType,
        "alertID": 0,
        "detectionTimestamp": 1,
        "score": 0.0,
    }
)


train_data = [1, 2, 3, 3, 2, 1, 2]
test_data = [3, 4, 3, 3, 1, 1, 2]

train_data_schemas = []
test_data_schemas = []


def init_schemas(i, data):
    return schemas.initialize(
        schemas.PARSER_SCHEMA,
        **{
            "EventID": 0,
            "logFormatVariables": {"level": str(data[i])},
            "variables": [str(data[i])],
            "log": f"Log message {str(i)}"
        }
    )


for i in range(len(train_data)):
    train_data_schemas.append(init_schemas(i, train_data))
    test_data_schemas.append(init_schemas(i, test_data))


class TestNewValueDetector:
    def test_train_data(self):
        detector = NewValueDetector(config=config)
        for log in train_data_schemas:
            detector.train(log)
        # After training, known values should include all training data values
        known_values = detector.known_values
        assert 0 in known_values
        assert "level" in known_values[0]
        assert known_values[0]["level"] == {"1", "2", "3"}
        assert "all" in known_values
        assert "level" in known_values["all"]
        assert known_values["all"]["level"] == {"1", "2", "3"}

    def test_detect_anomalous(self):
        detector = NewValueDetector(config=config)
        for log in train_data_schemas:
            detector.train(log)
        # Now test detection on anomalous data
        counter = 0
        for log in test_data_schemas:
            is_anomaly = detector.detect(log, output)
            if counter == 1:
                assert is_anomaly
                assert output.score > 0.0
            else:
                assert not is_anomaly
                assert output.score == 0.0
            counter += 1
