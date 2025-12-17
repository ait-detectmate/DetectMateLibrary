
from detectmatelibrary.outputs.json_output import JSONOutput, JSONOutputConfig


class TestJSONOutput:
    def test_do_output(self):
        config = JSONOutputConfig(path_folder=".")
        json_output = JSONOutput(name="TestJsonOutput", config=config)
        json_output.test_mode = True

        input_ = {
            "detectorID": "detector_1",
            "detectorType": "type_A",
            "alertID": 123,
            "detectionTimestamp": 1625079600,
            "logIDs": [1, 2, 3],
            "score": 0.95,
            "extractedTimestamps": [1625079601, 1625079602],
            "description": "Test alert",
            "alertsObtain": {"key": "value"},
            "receivedTimestamp": 1625079603,
        }

        output_ = {}

        json_output.do_output(input_, output_)

        assert output_["description"] == "Alert description: Test alert"
        assert output_["alertsObtain"] == {"key": "value"}
