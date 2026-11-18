"""Absolute paths to the files in tests/test_data/.

Tests never write into tests/test_data/; outputs go to the test's own
temporary directory.
"""
from pathlib import Path

TEST_DATA = Path(__file__).resolve().parent.parent / "test_data"

AUDIT_LOG = str(TEST_DATA / "audit.log")
AUDIT_TEMPLATES = str(TEST_DATA / "audit_templates.txt")
ANOMALY_LABELS = str(TEST_DATA / "audit_anomaly_labels.log")
AUDIT_NAMED_TEMPLATES = str(TEST_DATA / "audit_named_templates.csv")
AUDIT_PIPELINE_YAML = str(TEST_DATA / "audit_pipeline.yaml")
APACHE_LOG = str(TEST_DATA / "apache.log")
LOG_PATH = str(TEST_DATA / "logs.log")
TEST_CONFIG = str(TEST_DATA / "test_config.yaml")
TEST_TEMPLATES = str(TEST_DATA / "test_templates.txt")
NAMED_TEMPLATES_TXT = str(TEST_DATA / "test_named_templates.txt")
NAMED_TEMPLATES_CSV = str(TEST_DATA / "test_named_templates.csv")
PRE_TRACKER_STATE = TEST_DATA / "pre_tracker_state"
