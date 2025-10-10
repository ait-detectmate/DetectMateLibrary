"""Configuration module for DetectMate Library.

This module provides configuration classes for parsers, detectors, and
the main application.
"""

# Import all classes to maintain backward compatibility
from .parsers import ParserInstance, ParserConfig
from .detectors import DetectorInstance, DetectorConfig
from .app_config import AppConfig, load_config_from_yaml

__all__ = [
    # Parser classes
    "ParserInstance",
    "ParserConfig",

    # Variable classes
    "DetectorVarParams",
    "DetectorVariable",
    "HeaderVariable",

    # Detector classes
    "DetectorInstance",
    "DetectorConfig",

    # Main config class
    "AppConfig",

    # Utility functions
    "load_config_from_yaml",
]
