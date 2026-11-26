"""Facts about tests/test_data/audit.log used by several tests."""

# The header of every audit.log line, for the parsers' log_format.
LOG_FORMAT = "type=<Type> msg=audit(<Time>): <Content>"

# Configure/train on the first TRAIN_UNTIL lines, detect on the rest.
TRAIN_UNTIL = 1800
