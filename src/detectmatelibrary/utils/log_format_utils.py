from datetime import datetime
from typing import Tuple
import re

def apply_time_format(time_str: str, time_format: str) -> str:
    try:
        dt = datetime.strptime(time_str, time_format)
        return str(int(dt.timestamp()))
    except Exception:
        return "0"

def get_format_variables(
    regex: re.Pattern[str] | None, time_format: str, log: str
) -> Tuple[dict[str, str], str]:

    if regex is None:
        vars = {"Time": "0"}
    else:
        match = regex.search(log)
        vars = match.groupdict() if match else {"Time": "0"}
    if "Time" in vars and time_format:
        vars["Time"] = apply_time_format(vars["Time"], time_format)

    return vars, vars["Content"] if "Content" in vars else log

def generate_logformat_regex(log_format: str) -> Tuple[list[str], re.Pattern[str]]:
        """ 
        Function to generate regular expression to split log messages
        Args:
            log_format: log format
        Returns:
            headers: headers of log messages
            regex: regular expression to split log messages
        """
        headers = []
        splitters = re.split(r'(<[^<>]+>)', log_format)
        regex_str = ''
        for k in range(len(splitters)):
            if k % 2 == 0:
                splitter = re.sub(' +', '\\\s+', splitters[k])
                regex_str += splitter
            else:
                header = splitters[k].strip('<').strip('>')
                regex_str += '(?P<%s>.*?)' % header
                headers.append(header)
        regex = re.compile('^' + regex_str + '$')
        return headers, regex