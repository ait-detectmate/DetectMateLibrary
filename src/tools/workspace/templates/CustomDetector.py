from typing import Any, List

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary import schemas


class CustomDetectorConfig(CoreDetectorConfig):
    """Configuration for CustomDetector."""
    # You can change this to whatever method_type you need
    method_type: str = "custom_detector"


class CustomDetector(CoreDetector):
    """Template detector implementation based on CoreDetector.

    Replace this docstring with a description of what your detector does
    and how it should be used.
    """

    def __init__(
        self,
        name: str = "CustomDetector",
        config: CustomDetectorConfig | dict[str, Any] = CustomDetectorConfig(),
    ) -> None:

        # Allow passing either a config instance or a plain dict
        if isinstance(config, dict):
            config = CustomDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self._call_count = 0

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema,
    ) -> bool:
        """Run detection on parser output and populate the detector schema.

        :param input_: One or many ParserSchema instances
        :param output_: DetectorSchema instance to be mutated in-place
        :return: Detection result (True/False)
        """

        output_["description"] = "Dummy detection process"  # Description of the detection

        # Alternating pattern: True, False, True, False, etc
        self._call_count += 1
        pattern = [True, False]
        result = pattern[self._call_count % len(pattern)]
        if result:
            output_["score"] = 1.0  # Score of the detector
            output_["alertsObtain"]["type"] = "Anomaly detected by CustomDetector"  # Additional info

        return result
