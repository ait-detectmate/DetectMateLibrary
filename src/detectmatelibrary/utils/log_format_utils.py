from detectmatelibrary.utils.time_format_handler import TimeFormatHandler
from typing import Tuple
import re


def get_format_variables(
    regex: re.Pattern[str] | None, 
    time_format: str | None, 
    log: str,
    time_format_handler: TimeFormatHandler = TimeFormatHandler()
) -> Tuple[dict[str, str], str]:
    """
    Extract format variables from a log string using regex and time format.
    
    Args:
        regex: Compiled regex pattern to extract variables
        time_format: Time format string for parsing timestamps
        log: The log string to parse
        
    Returns:
        Tuple of (variables dictionary, content string)
    """
    if regex is None:
        vars = {"Time": "0"}
    else:
        match = regex.search(log)
        vars = match.groupdict() if match else {"Time": "0"}
    if "Time" in vars and time_format:
        vars["Time"] = time_format_handler.parse_timestamp(vars["Time"], time_format)

    return vars, vars["Content"] if "Content" in vars else log


def generate_logformat_regex(log_format: str) -> Tuple[list[str], re.Pattern[str]]:
    """
    Generate regular expression to split log messages based on format string.
    
    Args:
        log_format: Log format string with placeholders in angle brackets (e.g., '<Time> <Content>')
        
    Returns:
        Tuple of (headers list, compiled regex pattern)
    """
    headers = []
    splitters = re.split(r'(<[^<>]+>)', log_format)
    regex_str = ''
    for k in range(len(splitters)):
        if k % 2 == 0:
            splitter = re.sub(r' +', r'\\s+', splitters[k])
            regex_str += splitter
        else:
            header = splitters[k].strip('<').strip('>')
            regex_str += '(?P<%s>.*?)' % header
            headers.append(header)
    regex = re.compile('^' + regex_str + '$')
    return headers, regex