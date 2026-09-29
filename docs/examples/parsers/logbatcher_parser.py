# --8<-- [start:basic]
import yaml
from detectmatelibrary.parsers.logbatcher import LogBatcherParser

# LogBatcher sends logs to an LLM: put a real api_key in the YAML to parse.
# Without one, this only builds the parser.
with open("docs/examples/parsers/logbatcher_parser.yaml") as f:
    config = yaml.safe_load(f)
parser = LogBatcherParser(name="LogBatcherParser", config=config)

# with a real api_key:
#   output = parser.process(schemas.LogSchema({"logID": "1", "log": "User admin logged in from 192.168.1.10"}))
#   print(output["template"])   # e.g. "User <*> logged in from <*>"
# --8<-- [end:basic]

# --8<-- [start:ollama]
from detectmatelibrary.parsers.logbatcher import LogBatcherParser, LogBatcherParserConfig  # noqa: E402

# a local Ollama instance speaks the same API; here the config is built in Python
config = LogBatcherParserConfig(
    api_key="ollama",
    model="llama3",
    base_url="http://localhost:11434/v1",
)
parser = LogBatcherParser(name="LogBatcherParser", config=config)
# with Ollama running, parse exactly as above:
#   print(output["template"])   # e.g. "User <*> logged in from <*>"
#   print(output["variables"])  # e.g. ["admin", "192.168.1.10"]
# --8<-- [end:ollama]
