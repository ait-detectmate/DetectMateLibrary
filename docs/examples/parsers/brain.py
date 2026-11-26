# --8<-- [start:example_1]
import yaml

from detectmatelibrary import schemas
from detectmatelibrary.parsers.brain import BrainParser

with open("docs/examples/parsers/brain.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)


def log(text: str) -> schemas.LogSchema:
    return schemas.LogSchema({"log": text})


training_logs = ("hello there, general kenobi!", "hello there, captain kenobi!")
matching_log = "hello there, sergeant kenobi!"
new_training_log = "bella ciao bella ciao"
parser = BrainParser(name="BrainParser", config=config)

for text in training_logs:
    print(parser.process(log(text))["template"])  # templates not yet generated
print(parser.process(log(matching_log))["template"])  # hello there <*> kenobi

parser.update_state("keep_training")
parser.process(log(new_training_log))
parser.update_state("stop_training")

print(parser.process(log(matching_log))["template"])  # hello there <*> kenobi
# --8<-- [end:example_1]

# --8<-- [start:example_2]
config["parsers"]["BrainParser"]["params"]["reset_in_post_train"] = True
parser = BrainParser(name="BrainParser", config=config)

for text in training_logs:
    parser.process(log(text))
print(parser.process(log(matching_log))["template"])  # hello there <*> kenobi

parser.update_state("keep_training")
parser.process(log(new_training_log))
parser.update_state("stop_training")

print(parser.process(log(matching_log))["template"])  # template not found
print(parser.process(log(new_training_log))["template"])  # bella ciao bella ciao
# --8<-- [end:example_2]
