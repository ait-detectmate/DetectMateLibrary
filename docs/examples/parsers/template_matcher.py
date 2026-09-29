# --8<-- [start:example]
import yaml
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary import schemas

with open("docs/examples/parsers/template_matcher.yaml") as f:
    config = yaml.safe_load(f)
parser = MatcherParser(name="MatcherParser", config=config)

parsed = parser.process(schemas.LogSchema({
    "logID": "0",
    "log": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'",
}))
print(parsed.EventID)    # 0: the first template in the file
print(parsed.template)   # pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>
print(parsed.variables)  # ('9699', '0', '4294967295', '4294967295', 'accounting', '"root"\'')
# --8<-- [end:example]
