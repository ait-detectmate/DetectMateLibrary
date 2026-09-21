# --8<-- [start:basic]
from detectmatelibrary.parsers.logbatcher import LogBatcherParser, LogBatcherParserConfig

# instantiate the parser (config as a typed config object)
# note: LogBatcher sends logs to an LLM, so a real api_key is required
#       to actually parse. Here we only build the parser.
config = LogBatcherParserConfig(
    api_key="<YOUR_API_KEY>",
    model="gpt-4o-mini",
    batch_size=10,
)

parser = LogBatcherParser(name="LogBatcherParser", config=config)

# to parse a log, provide a real api_key above and call:
#   output = schemas.ParserSchema()
#   parser.parse(input_log, output)
#   print(output["template"])   # e.g. "User <*> logged in from <*>"
# --8<-- [end:basic]

# --8<-- [start:ollama]
from detectmatelibrary.parsers.logbatcher import LogBatcherParser, LogBatcherParserConfig

config = LogBatcherParserConfig(
    api_key="ollama",
    model="llama3",
    base_url="http://localhost:11434/v1",
    batch_size=10,
)
parser = LogBatcherParser(name="LogBatcherParser", config=config)
# with a running Ollama instance, parse a log like this:
#   input_log = schemas.LogSchema({
#       "logID": "1",
#       "log": "User admin logged in from 192.168.1.10",
#   })
#   output = schemas.ParserSchema()
#   parser.parse(input_log, output)
#   print(output["template"])   # e.g. "User <*> logged in from <*>"
#   print(output["variables"])  # e.g. ["admin", "192.168.1.10"]
# --8<-- [end:ollama]

# --8<-- [start:config]
from detectmatelibrary.parsers.logbatcher import LogBatcherParser

# same parser, but configured from a plain dict instead of a config object
cfg = {
    "parsers": {
        "LogBatcher": {
            "method_type": "logbatcher_parser",
            "params": {
                "api_key": "<YOUR_API_KEY>",
                "model": "gpt-4o-mini",
                "batch_size": 10,
            },
        }
    }
}

parser = LogBatcherParser(name="LogBatcher", config=cfg)
# --8<-- [end:config]