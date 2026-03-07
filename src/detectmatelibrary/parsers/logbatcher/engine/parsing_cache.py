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

from hashlib import sha256
import re
import sys
from types import FrameType
from typing import Any, Dict, List, Match, Optional, Tuple

sys.setrecursionlimit(1000000)

import re
import signal

class TimeoutException(Exception):
    pass

def timeout_handler(_signum: int, _frame: Optional[FrameType]) -> None:
    raise TimeoutException()

def safe_search(pattern: str, string: str, timeout: int = 1) -> Optional[Match[str]]:
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        result = re.search(pattern, string)
    except TimeoutException:
        result = None
    finally:
        signal.alarm(0)
    return result

# _PATTERN = re.compile(r'(?:<\*>|\b\d+\b|[\s\/,:._-]+)')
# def old_standardize(log: str) -> str:
#     return _PATTERN.sub('', log)

# TODO: logb2 v3.1
_PATTERN1 = re.compile(r'/([^/]*)(?=/)')  # path
_PATTERN2 = re.compile(r'\d')               # digit
_PATTERN3 = re.compile(r'[\/:,._-]+')        # : , . _ -
_PATTERN4 = re.compile(r'\s')           # space

def standardize(input_string: str) -> str:
    result = _PATTERN1.sub('', input_string)
    result = _PATTERN2.sub('', result)
    result = _PATTERN3.sub('', result)
    result = _PATTERN4.sub('', result)
    return result

def print_tree(move_tree: Dict[str, Any], indent: str = ' ') -> None:
    for key, value in move_tree.items():
        if isinstance(value, dict):
            print(f'{indent}|- {key}')
            print_tree(value, indent + '|  ')
        elif isinstance(value, tuple):
            print(f'{indent}|- {key}: tuple')
        else:
            print(f'{indent}|- {key}: {value}')


def lcs_similarity(X: List[str], Y: List[str]) -> float:
    m, n = len(X), len(Y)
    c = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if X[i - 1] == Y[j - 1]:
                c[i][j] = c[i - 1][j - 1] + 1
            else:
                c[i][j] = max(c[i][j - 1], c[i - 1][j])
    return 2 * c[m][n] / (m + n)


class ParsingCache:
    def __init__(self) -> None:
        self.template_tree: Dict[str, Any] = {}
        self.template_list: List[str] = []
        self.hashing_cache: Dict[str, Tuple[str, str, int]] = {}
        self.variable_candidates: List[str] = []
        self.hit_num: int = 0

    def add_templates(
        self,
        event_template: str,
        insert: bool = True,
        relevant_templates: Optional[List[str]] = None,
        refer_log: str = '',
    ) -> Tuple[int, Optional[str], Optional[bool]]:

            # if "<*>" not in event_template:
            #     self.template_tree["$CONSTANT_TEMPLATE$"][event_template] = event_template
            #     continue
            # original_template = event_template
            # event_template = self._preprocess_template(event_template)
            #print("event template after preprocess: ", event_template)
        if relevant_templates is None:
            relevant_templates = []
        template_tokens = message_split(event_template)
        if not template_tokens or event_template == "<*>":
            return -1, None, None
        if insert or len(relevant_templates) == 0:
            id = self.insert(event_template, template_tokens, len(self.template_list), refer_log)
            self.template_list.append(event_template)
            return id,None,None
        # print("relevant templates: ", relevant_templates)
        max_similarity = 0
        similar_template = None
        for rt in relevant_templates:
            splited_template1, splited_template2 = rt.split(), event_template.split()
            if len(splited_template1) != len(splited_template2):
                continue 
            similarity = lcs_similarity(splited_template1, splited_template2)
            if similarity > max_similarity:
                max_similarity = similarity
                similar_template = rt
        if max_similarity > 0.8:
            success, id = self.modify(similar_template, event_template, refer_log)
            if not success:
                id = self.insert(event_template, template_tokens, len(self.template_list), refer_log)
                self.template_list.append(event_template)
            return id, similar_template, success
        else:
            id = self.insert(event_template, template_tokens, len(self.template_list), refer_log)
            self.template_list.append(event_template)
            return id,None,None
            #print("template tokens: ", template_tokens)
            
    def insert(self, event_template: str, template_tokens: List[str], template_id: int, refer_log: str = '') -> int:

        standardized = standardize(event_template)
        hash_key = sha256(standardized.encode()).hexdigest()
        self.hashing_cache[hash_key] = (standardized, event_template, template_id)

        start_token = template_tokens[0]
        if start_token not in self.template_tree:
            self.template_tree[start_token] = {}
        move_tree = self.template_tree[start_token]

        tidx = 1
        while tidx < len(template_tokens):
            token = template_tokens[tidx]
            if token not in move_tree:
                move_tree[token] = {}
            move_tree = move_tree[token]
            tidx += 1

        move_tree["".join(template_tokens)] = (
            sum(1 for s in template_tokens if s != "<*>"),
            template_tokens.count("<*>"),
            event_template,
            template_id,
            refer_log
        )  # statistic length, count of <*>, original_log, template_id
        return template_id

    def modify(self, similar_template: str, event_template: str, refer_log: str) -> Tuple[bool, int]:
        merged_template = []
        similar_tokens = similar_template.split()
        event_tokens = event_template.split()
        i = 0
        for token in similar_tokens:
            if token == event_tokens[i]:
                merged_template.append(token)
            else:
                merged_template.append("<*>")
            i += 1
        merged_template = " ".join(merged_template)
        success, old_ids = self.delete(similar_template)
        if not success:
            return False, -1
        self.insert(merged_template, message_split(merged_template), old_ids, refer_log)
        self.template_list[old_ids] = merged_template
        return True, old_ids
        
    
    def delete(self, event_template: str) -> Tuple[bool, int | List[Any]]:
        template_tokens = message_split(event_template)
        start_token = template_tokens[0]
        if start_token not in self.template_tree:
            return False, []
        move_tree = self.template_tree[start_token]

        tidx = 1
        while tidx < len(template_tokens):
            token = template_tokens[tidx]
            if token not in move_tree:
                return False, []
            move_tree = move_tree[token]
            tidx += 1
        old_id = move_tree["".join(template_tokens)][3]
        del move_tree["".join(template_tokens)]
        return True, old_id


    def match_event(self, log: str) -> Tuple[str, Any, List[str]]:
        standardized = standardize(log)
        hash_key = sha256(standardized.encode()).hexdigest()
        if hash_key in self.hashing_cache:
            cached_str, template, id = self.hashing_cache[hash_key]
            if cached_str == standardized:
                self.hit_num += 1
                return template, id, []
        results = tree_match(self.template_tree, self.template_list, log)
        if results[0] != "NoMatch":
            standardized = standardize(log)
            hash_key = sha256(standardized.encode()).hexdigest()
            self.hashing_cache[hash_key] = (standardized, results[0], results[1])
        return results


    def _preprocess_template(self, template: str) -> str:
        return template


def post_process_tokens(tokens: List[str], punc: str) -> List[str]:
    excluded_str = ['=', '|', '(', ')', ";"]
    for i in range(len(tokens)):
        if tokens[i].find("<*>") != -1:
            tokens[i] = "<*>"
        else:
            new_str = ""
            for s in tokens[i]:
                if (s not in punc and s != ' ') or s in excluded_str:
                    new_str += s
            tokens[i] = new_str
    return tokens


def message_split(message: str) -> List[str]:
    punc = "!\"#$%&'()+,-/;:=?@.[\\]^_`{|}~"
    splitters = "\\s\\" + "\\".join(punc)
    splitter_regex = re.compile("([{}])".format(splitters))
    tokens = re.split(splitter_regex, message)

    tokens = list(filter(lambda x: x != "", tokens))
    
    #print("tokens: ", tokens)
    tokens = post_process_tokens(tokens, punc)

    tokens = [
        token.strip()
        for token in tokens
        if token != "" and token != ' ' 
    ]
    tokens = [
        token
        for idx, token in enumerate(tokens)
        if not (token == "<*>" and idx > 0 and tokens[idx - 1] == "<*>")
    ]
    return tokens



def tree_match(match_tree: Dict[str, Any], template_list: List[str], log_content: str) -> Tuple[str, Any, List[str]]:
    log_tokens = message_split(log_content)
    template, template_id, refer_log, relevant_templates = match_template(match_tree, log_tokens)
    # length matters
    if template:
        if abs(len(log_content.split()) - len(refer_log.split())) <= 1:
            return (template, template_id, relevant_templates)
    elif len(relevant_templates) > 0:
        if match_log(log_content, relevant_templates[0]):
            return (relevant_templates[0], template_list.index(relevant_templates[0]), relevant_templates)
    return ("NoMatch", "NoMatch", relevant_templates)

def match_log(log: str, template: str) -> bool:
    pattern_parts = template.split("<*>")
    pattern_parts_escaped = [re.escape(part) for part in pattern_parts]
    regex_pattern = "(.*?)".join(pattern_parts_escaped)
    regex = "^" + regex_pattern + "$"  
    matches = safe_search(regex, log)

    if matches == None:
        return False
    else:
        return True #all(len(var.split()) == 1 for var in matches.groups())

def match_template(
    match_tree: Dict[str, Any], log_tokens: List[str]
) -> Tuple[Any, Any, str, List[str]]:
    results = []
    find_results = find_template(match_tree, log_tokens, results, [], 1)
    relevant_templates = find_results[1]
    if len(results) > 1:
        new_results = []
        for result in results:
            if result[0] is not None and result[1] is not None and result[2] is not None:
                new_results.append(result)
    else:
        new_results = results
    if len(new_results) > 0:
        if len(new_results) > 1:
            new_results.sort(key=lambda x: (-x[1][0], x[1][1]))
        return new_results[0][1][2], new_results[0][1][3], new_results[0][1][4], relevant_templates
    return False, False, '', relevant_templates


def get_all_templates(move_tree: Dict[str, Any]) -> List[str]:
    result = []
    for key, value in move_tree.items():
        if isinstance(value, tuple):
            result.append(value[2])
        else:
            result = result + get_all_templates(value)
    return result


def find_template(
    move_tree: Dict[str, Any],
    log_tokens: List[str],
    result: List[Tuple[Any, ...]],
    parameter_list: List[str],
    depth: int,
) -> Tuple[bool, List[str]]:
    flag = 0 # no futher find
    if len(log_tokens) == 0:
        for key, value in move_tree.items():
            if isinstance(value, tuple):
                result.append((key, value, tuple(parameter_list)))
                flag = 2 # match
        if "<*>" in move_tree:
            parameter_list.append("")
            move_tree = move_tree["<*>"]
            if isinstance(move_tree, tuple):
                result.append(("<*>", None, None))
                flag = 2 # match
            else:
                for key, value in move_tree.items():
                    if isinstance(value, tuple):
                        result.append((key, value, tuple(parameter_list)))
                        flag = 2 # match
        # return (True, [])
    else:
        token = log_tokens[0]

        relevant_templates = []
        if token in move_tree:
            find_result = find_template(move_tree[token], log_tokens[1:], result, parameter_list,depth+1)
            if find_result[0]:
                flag = 2 # match
            elif flag != 2:
                flag = 1 # futher find but no match
                relevant_templates = relevant_templates + find_result[1]
        if "<*>" in move_tree:
            if isinstance(move_tree["<*>"], dict):
                next_keys = move_tree["<*>"].keys()
                next_continue_keys = []
                for nk in next_keys:
                    nv = move_tree["<*>"][nk]
                    if not isinstance(nv, tuple):
                        next_continue_keys.append(nk)
                idx = 0
                # print("len : ", len(log_tokens))
                while idx < len(log_tokens):
                    token = log_tokens[idx]
                    # print("try", token)
                    if token in next_continue_keys:
                        # print("add", "".join(log_tokens[0:idx]))
                        parameter_list.append("".join(log_tokens[0:idx]))
                        # print("End at", idx, parameter_list)
                        find_result = find_template(
                            move_tree["<*>"], log_tokens[idx:], result, parameter_list,depth+1
                        )
                        if find_result[0]:
                            flag = 2 # match
                        elif flag != 2:
                            flag = 1 # futher find but no match
                            relevant_templates = relevant_templates + find_result[1]
                        if parameter_list:
                            parameter_list.pop()
                        next_continue_keys.remove(token)
                    idx += 1
                if idx == len(log_tokens):
                    parameter_list.append("".join(log_tokens[0:idx]))
                    find_result = find_template(
                        move_tree["<*>"], log_tokens[idx + 1 :], result, parameter_list,depth+1
                    )
                    if find_result[0]:
                        flag = 2 # match
                    else:
                        if flag != 2:
                            flag = 1
                        # relevant_templates = relevant_templates + find_result[1]
                    if parameter_list:
                        parameter_list.pop()
    if flag == 2:
        return (True, [])
    if flag == 1:
        return (False, relevant_templates)
    if flag == 0:
        # print(log_tokens, flag)
        if depth >= 2:
            return (False, get_all_templates(move_tree))
        else:
            return (False, [])