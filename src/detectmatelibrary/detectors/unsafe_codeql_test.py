# codeql_test.py
from tempfile import mktemp
import re

def insecure_tmp():
    filename = mktemp()
    with open(filename, "w") as f:
        f.write("test")

def bad_regex(user_input):
    return re.search(user_input, "abc")

def unsafe_eval(user_input):
    return eval(user_input)
