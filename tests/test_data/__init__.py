from pathlib import Path

AUDIT_LOG = Path(__file__).resolve().parent / "test_data/audit.log"
AUDIT_TEMPLATES = Path(__file__).resolve().parent / "test_data/audit_templates.txt"
ANOMALY_LABELS = Path(__file__).resolve().parent / "test_data/audit_anomaly_labels.log"
LOG_FORMAT = "type=<Type> msg=audit(<Time>): <Content>"
TRAIN_UNTIL = 1800
LOG_PATH = Path(__file__).resolve().parent / "test_data/logs.log"
TEST_CONFIG = Path(__file__).resolve().parent / "test_data/test_config.yaml"
DUMMY_TXT_PATH = Path(__file__).resolve().parent / "test_data/dummy.txt"
DUMMY_TXT_PATH2 = Path(__file__).resolve().parent / "test_data/dummy2.txt"
DUMMY_JSON_PATH = Path(__file__).resolve().parent / "test_data/dummy.json"
DUMMY_JSON_PATH2 = Path(__file__).resolve().parent / "test_data/dummy2.json"
DUMMY_YAML_PATH = Path(__file__).resolve().parent / "test_data/dummy.yaml"
DUMMY_YAML_PATH2 = Path(__file__).resolve().parent / "test_data/dummy2.yaml"
TEST_TEMPLATES = Path(__file__).resolve().parent / "test_data/test_templates.txt"
NAMED_TEMPLATES_TXT = Path(__file__).resolve().parent / "test_data/test_named_templates.txt"
NAMED_TEMPLATES_CSV = Path(__file__).resolve().parent / "test_data/test_named_templates.csv"
