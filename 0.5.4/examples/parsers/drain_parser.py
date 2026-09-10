# flake8: noqa

# --8<-- [start:example_1]
from detectmatelibrary.parsers.drain import DrainParser
from detectmatelibrary import schemas

# instantiate parser (config can be a dict or a config object)
config_dict = {
    "parsers": {
        "DrainParser": {
            "method_type": "drain_parser",
            "data_use_training": 2,
            "reset_in_post_train": False,
        }
    }
}

parser = DrainParser(config=config_dict)

parsed = parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "hello there <*> kenobi"

parser.update_state("keep_training")
parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
parser.update_state("stop_training")

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "hello there <*> kenobi"
# --8<-- [end:example_1]


# --8<-- [start:example_2]
from detectmatelibrary.parsers.drain import DrainParser
from detectmatelibrary import schemas

# instantiate parser (config can be a dict or a config object)
config_dict = {
    "parsers": {
        "DrainParser": {
            "method_type": "drain_parser",
            "data_use_training": 2,
            "reset_in_post_train": False,
        }
    }
}

parser = DrainParser(config=config_dict)

parsed = parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "hello there <*> kenobi"

parser.update_state("keep_training")
parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
parser.update_state("stop_training")

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "template not found"
# --8<-- [end:example_2]
