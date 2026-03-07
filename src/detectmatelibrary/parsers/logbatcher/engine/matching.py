# MIT License
#
# Copyright (c) 2024 LogIntelligence
#
# Based on LogBatcher (https://github.com/LogIntelligence/LogBatcher)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import re
from types import FrameType
from typing import Optional, Tuple

from .cluster import Cluster

import signal

class TimeoutException(Exception):
    pass

def timeout_handler(_signum: int, _frame: Optional[FrameType]) -> None:
    raise TimeoutException()

def safe_search(pattern: str, string: str, timeout: float = 0.5) -> Optional[re.Match[str]]:
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        result = re.search(pattern, string)
    except TimeoutException:
        result = None
    finally:
        signal.alarm(0)
    return result


# @timeout(10)
def extract_variables(log: str, template: str) -> Optional[Tuple[str, ...]]:
    log = re.sub(r'\s+', ' ', log.strip()) # DS
    pattern_parts = template.split("<*>")
    pattern_parts_escaped = [re.escape(part) for part in pattern_parts]
    regex_pattern = "(.*?)".join(pattern_parts_escaped)
    regex = "^" + regex_pattern + "$"  
    # matches = re.search(regex, log)
    matches = safe_search(regex, log, 1)
    if matches:
        return matches.groups()
    else:
        return None

def matches_template(log: str, cached_pair: Tuple[str, str]) -> Optional[str]:

    reference_log = cached_pair[0]
    template = cached_pair[1]

    # length matters
    if abs(len(log.split()) - len(reference_log.split())) > 1:
        return None

    try:
        groups = extract_variables(log, template)
    except:
        groups = None
    if groups == None:
        return None

    # consider the case where the varaible is empty
    parts = []
    for index, part in enumerate(template.split("<*>")):
        parts.append(part)
        if index < len(groups):
            if groups[index] == '':
                parts.append('')
            else:
                parts.append('<*>')

    return ''.join(parts)



def prune_from_cluster(template: str, cluster: Cluster) -> Tuple[Cluster, Cluster]:

    new_cluster = Cluster()
    logs, indexs = cluster.logs, cluster.indexs
    for log, index in zip(logs, indexs):
        if extract_variables(log, template) == None:
            new_cluster.append_log(log, index)
    if new_cluster.size != 0:
        old_logs = [log for log in logs if log not in new_cluster.logs]
        old_indexs = [index for index in indexs if index not in new_cluster.indexs]
        cluster.logs = old_logs
        cluster.indexs = old_indexs
        # print(f"prune {new_cluster.size} logs from {len(logs)} logs in mathcing process")
    return cluster, new_cluster