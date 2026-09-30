# --8<-- [start:example_1]
import yaml
from detectmatelibrary.parsers.drain import DrainParser
from detectmatelibrary import schemas

with open("docs/examples/parsers/drain_parser.yaml") as f:
    config = yaml.safe_load(f)


def log(text: str) -> schemas.LogSchema:
    return schemas.LogSchema({"log": text})


parser = DrainParser(name="DrainParser", config=config)

# the first 2 logs train the parser (data_use_training: 2)
print(parser.process(log("hello there, general kenobi!"))["template"])  # templates not yet generated
print(parser.process(log("hello there, captain kenobi!"))["template"])  # templates not yet generated
print(parser.process(log("hello there, sargent kenobi!"))["template"])  # hello there <*> kenobi

# train on one more log, then go back to parsing
parser.update_state("keep_training")
parser.process(log("bella ciao bella ciao"))
parser.update_state("stop_training")

print(parser.process(log("hello there, sargent kenobi!"))["template"])  # hello there <*> kenobi
# --8<-- [end:example_1]

# --8<-- [start:example_2]
# the same configuration, but the parser forgets its templates after each training round
config["parsers"]["DrainParser"]["params"]["reset_in_post_train"] = True
parser = DrainParser(name="DrainParser", config=config)

parser.process(log("hello there, general kenobi!"))
parser.process(log("hello there, captain kenobi!"))
print(parser.process(log("hello there, sargent kenobi!"))["template"])  # hello there <*> kenobi

parser.update_state("keep_training")
parser.process(log("bella ciao bella ciao"))
parser.update_state("stop_training")

# template not found: the second round only learned "bella ciao bella ciao"
print(parser.process(log("hello there, sargent kenobi!"))["template"])
# --8<-- [end:example_2]
