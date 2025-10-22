import sys
from pathlib import Path

from components.common.config.parser import CoreParserConfig

# add the src directory to path so internal imports work
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

# TODO: do these need to be part of the public API?
from components.common.config.detector import CoreDetectorConfig
from components.common.core import CoreComponent, CoreConfig
from components.common.reader import CoreReader, CoreReaderConfig
from components.common.parser import CoreParser
from components.common.detector import CoreDetector

# Import subpackages
from . import detectors

# Re-export for direct imports
from .detectors import RandomDetector, RandomDetectorConfig, NewValueDetector, NewValueDetectorConfig

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

    # submodule access
    # TODO: maybe keep only these?
    "detectors"
]
