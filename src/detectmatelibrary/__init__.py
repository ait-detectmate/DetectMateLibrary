import sys
from pathlib import Path


# add the src directory to path so internal imports work
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from components.common.core import CoreComponent, CoreConfig
from components.common.reader import CoreReader, CoreReaderConfig
from components.common.parser import CoreParser, CoreParserConfig
from components.common.detector import CoreDetector, CoreDetectorConfig

from components.detectors.RandomDetector import RandomDetector, RandomConfig


__all__ = [
    "CoreComponent",
    "CoreConfig",
    "CoreReader",
    "CoreReaderConfig",
    "CoreParser",
    "CoreParserConfig",
    "CoreDetector",
    "CoreDetectorConfig",
    "RandomDetector",
    "RandomConfig",
]
