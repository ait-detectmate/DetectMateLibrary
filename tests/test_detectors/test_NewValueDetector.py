from components.common.core import CoreConfig
from components.detectors.NewValueDetector import NewValueDetector


class TestNewValueDetector():
    def test_initialize_default(self) -> None:
        detector = NewValueDetector(name="NewValueDetector", config={})

        assert isinstance(detector, NewValueDetector)
        assert detector.name == "NewValueDetector"
        assert isinstance(detector.config, CoreConfig)

#     def test_train_and_detect(self) -> None:
#         detector = NewValueDetector(name="NewValueDetector", config={})
#         data = schemas.initialize(schemas.ParserSchema, **{"log": "unique log"})
#         detector.train([data])
#         assert data in detector.value_set

#         detect_result = detector.detect(data)
#         assert isinstance(detect_result, schemas.DETECTOR_SCHEMA)
#         assert hasattr(detect_result, "score")
#         assert detect_result.score == 0.99

#     def test_train_with_multiple_items(self) -> None:
#         detector = NewValueDetector()
#         data1 = schemas.initialize(schemas.ParserSchema, **{"log": "log1"})
#         data2 = schemas.initialize(schemas.ParserSchema, **{"log": "log2"})
#         detector.train([data1, data2])
#         assert data1 in detector.value_set
#         assert data2 in detector.value_set
#         assert len(detector.value_set) == 2

#     def test_detect_with_list_input(self) -> None:
#         detector = NewValueDetector()
#         data1 = schemas.initialize(schemas.ParserSchema, **{"log": "log1"})
#         data2 = schemas.initialize(schemas.ParserSchema, **{"log": "log2"})
#         result = detector.detect([data1, data2])
#         assert isinstance(result, schemas.DETECTOR_SCHEMA)
#         assert result.score == 0.99

#     def test_train_with_empty_list(self) -> None:
#         detector = NewValueDetector()
#         detector.train([])
#         assert len(detector.value_set) == 0

#     def test_detect_with_empty_list(self) -> None:
#         detector = NewValueDetector()
#         result = detector.detect([])
#         assert isinstance(result, schemas.DETECTOR_SCHEMA)
#         assert result.score == 0.99

# if __name__ == "__main__":
#     pytest.main([__file__, "-v", "-s"])
