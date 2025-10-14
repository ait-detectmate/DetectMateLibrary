import sys
from pathlib import Path


# add the src directory to path so internal imports work
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

# TODO: do these need to be part of the public API?
from components.common.core import CoreComponent, CoreConfig
from components.common.reader import CoreReader, CoreReaderConfig
from components.common.parser import CoreParser, CoreParserConfig
from components.common.detector import CoreDetector, CoreDetectorConfig

# specific implementations
# TODO: do we need direct imports?
from components.readers.log_file import LogFileReader, LogFileConfig
from components.detectors.RandomDetector import RandomDetector, RandomConfig
from components.detectors.NewValueDetector import NewValueDetector, NVDConfig

# submodule aliases for better organization
from components import readers, detectors, parsers


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
    "readers", "detectors", "parsers"
]
