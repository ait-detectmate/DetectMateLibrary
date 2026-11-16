
# flake8: noqa
log_path = "tests/test_data/logs.log"
output_path = "dummy"


# --8<-- [start:example_1]
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcher
from detectmatelibrary.helper.from_to import From

parser = TemplateCppTreeMatcher()

for log in From.log(parser, in_path=log_path, do_process=False):
    print(log)

# --8<-- [end:example_1]


# --8<-- [start:example_2]
from detectmatelibrary.helper.from_to import To

parser = TemplateCppTreeMatcher()
for log in From.log(parser, in_path=log_path, do_process=False):
    To.json(log, output_path)
# --8<-- [end:example_2]


# --8<-- [start:example_3]
from detectmatelibrary.helper.from_to import FromTo

parser = TemplateCppTreeMatcher()
for parsed_log in FromTo.log2json(parser, log_path, output_path):
    pass
# --8<-- [end:example_3]


import os
os.remove(output_path)
