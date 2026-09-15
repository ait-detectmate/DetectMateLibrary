# flake8: noqa

# --8<-- [start:example_1]

from detectmatelibrary.parsers.autoparser import AutoParser

from detectmatelibrary.helper.from_to import From

config_dict = {
        "parsers": {
            "AutoParser": {
                "method_type": "auto_parser",
                "data_use_training": 10,
            }
        }
    }
parser = AutoParser(config=config_dict)
path = "tests/test_data/audit.log"

for j, parsed_log in enumerate(From.log(parser, path)):
    if j == 15:
        break

print(parsed_log["template"])  # Returns the parsed log as audit

# --8<-- [end:example_1]

# --8<-- [start:example_2]

from detectmatelibrary.parsers.autoparser import AutoParser

from detectmatelibrary.helper.from_to import From

config_dict = {
        "parsers": {
            "AutoParser": {
                "method_type": "auto_parser",
                "data_use_training": 10,
                "params": {
                    "fix_type": "Audit"  # Fix search to only Audit
                }
            }
        }
    }
parser = AutoParser(config=config_dict)
path = "tests/test_data/audit.log"

for j, parsed_log in enumerate(From.log(parser, path)):
    if j == 15:
        break

print(parsed_log["template"])  # Returns the parsed log as audit

# --8<-- [end:example_2]
