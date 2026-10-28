# --8<-- [start:example_1]
import yaml
from detectmatelibrary.parsers.autoparser import AutoParser
from detectmatelibrary.helper.from_to import From

with open("docs/examples/parsers/auto_parser.yaml") as f:
    config = yaml.safe_load(f)
parser = AutoParser(name="AutoParser", config=config)

for j, parsed_log in enumerate(From.log(parser, "tests/test_data/audit.log")):
    if j == 15:
        break

print(parsed_log["template"])  # pid <*> uid <*> auid <*> ses <*> msg op <*> acct <*> exe <*> ...
# --8<-- [end:example_1]

# --8<-- [start:example_2]
# the same configuration, but skip the detection and fix the log type to Audit
config["parsers"]["AutoParser"]["params"]["fix_type"] = "Audit"
parser = AutoParser(name="AutoParser", config=config)

for j, parsed_log in enumerate(From.log(parser, "tests/test_data/audit.log")):
    if j == 15:
        break

print(parsed_log["template"])  # same template, without the type detection
# --8<-- [end:example_2]
