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
from typing import Optional, Set

def post_process(response: str) -> str:

    response = response.replace('\n', '')
    first_backtick_index = response.find('`')
    last_backtick_index = response.rfind('`')
    if first_backtick_index == -1 or last_backtick_index == -1 or first_backtick_index == last_backtick_index:
        tmps = []
    else:
        tmps = response[first_backtick_index: last_backtick_index + 1].split('`')
    for tmp in tmps:
        if tmp.replace(' ','').replace('<*>','') == '':
            tmps.remove(tmp)
    tmp = ''
    if len(tmps) == 1:
        tmp = tmps[0]
    if len(tmps) > 1:
        tmp = max(tmps, key=len)

    template = re.sub(r'\{\{.*?\}\}', '<*>', tmp)
    template = re.sub(r'\$\{.*?\}', '<*>', template)
    template = correct_single_template(template)
    if template.replace('<*>', '').replace(' ','') == '':
        template = ''

    return template

def exclude_digits(string: str) -> bool:
    '''
    exclude the digits-domain words from partial constant
    '''
    pattern = r'\d'
    digits = re.findall(pattern, string)
    if len(digits) == 0 or string[0].isalpha() or any(c.isupper() for c in string):
        return False
    elif len(digits) >= 4:
        return True
    else:
        return len(digits) / len(string) > 0.3

def correct_single_template(template: str, user_strings: Optional[Set[str]] = None) -> str:
    """Apply all rules to process a template.

    DS (Double Space)
    BL (Boolean)
    US (User String)
    DG (Digit)
    PS (Path-like String)
    WV (Word concatenated with Variable)
    DV (Dot-separated Variables)
    CV (Consecutive Variables)

    """

    boolean = {'true', 'false'}
    default_strings = {'null', 'root'} # 'null', 'root', 'admin'
    path_delimiters = {  # reduced set of delimiters for tokenizing for checking the path-like strings
        r'\s', r'\,', r'\!', r'\;', r'\:',
        r'\=', r'\|', r'\"', r'\'', r'\+',
        r'\[', r'\]', r'\(', r'\)', r'\{', r'\}'
    }
    token_delimiters = path_delimiters.union({  # all delimiters for tokenizing the remaining rules
        r'\.', r'\-', r'\@', r'\#', r'\$', r'\%', r'\&', r'\/'
    })

    if user_strings:
        default_strings = default_strings.union(user_strings)
    # default_strings = {}

    # apply DS
    # Note: this is not necessary while postprorcessing
    template = template.strip()
    template = re.sub(r'\s+', ' ', template)

    # apply PS
    p_tokens = re.split('(' + '|'.join(path_delimiters) + ')', template)
    new_p_tokens = []
    for p_token in p_tokens:
        # print(p_token)
        # if re.match(r'^(\/[^\/]+)+$', p_token) or re.match(r'^([a-zA-Z0-9-]+\.){2,}[a-zA-Z]+$', p_token):
        if re.match(r'^(\/[^\/]+)+\/?$', p_token) or re.match(r'.*/.*\..*', p_token) or re.match(r'^([a-zA-Z0-9-]+\.){3,}[a-z]+$', p_token):
        # or re.match(r'^([a-z0-9-]+\.){2,}[a-z]+$', p_token)
            p_token = '<*>'
        
        new_p_tokens.append(p_token)
    template = ''.join(new_p_tokens)
    # tokenize for the remaining rules
    tokens = re.split('(' + '|'.join(token_delimiters) + ')', template)  # tokenizing while keeping delimiters
    new_tokens = []
    for token in tokens:
        # apply BL, US
        for to_replace in boolean.union(default_strings):
            # if token.lower() == to_replace.lower():
            if token == to_replace:
                token = '<*>'

        # apply DG
        # Note: hexadecimal num also appears a lot in the logs
        # if re.match(r'^\d+$', token) or re.match(r'\b0[xX][0-9a-fA-F]+\b', token):
        #     token = '<*>'
        if exclude_digits(token):
            token = '<*>'

        # apply WV
        if re.match(r'^[^\s\/]*<\*>[^\s\/]*$', token) or re.match(r'^<\*>.*<\*>$', token):
            token = '<*>'
        # collect the result
        new_tokens.append(token)

    # make the template using new_tokens
    template = ''.join(new_tokens)

    # Substitute consecutive variables only if separated with any delimiter including "." (DV)
    while True:
        prev = template
        template = re.sub(r'<\*>\.<\*>', '<*>', template)
        if prev == template:
            break

    # Substitute consecutive variables only if not separated with any delimiter including space (CV)
    # NOTE: this should be done at the end
    while True:
        prev = template
        template = re.sub(r'<\*><\*>', '<*>', template)
        if prev == template:
            break

    while "#<*>#" in template:
        template = template.replace("#<*>#", "<*>")

    while "<*>:<*>" in template:
        template = template.replace("<*>:<*>", "<*>")

    while "<*>/<*>" in template:
        template = template.replace("<*>/<*>", "<*>")

    while " #<*> " in template:
        template = template.replace(" #<*> ", " <*> ")

    while "<*>:<*>" in template:
        template = template.replace("<*>:<*>", "<*>")

    while "<*>#<*>" in template:
        template = template.replace("<*>#<*>", "<*>")

    while "<*>/<*>" in template:
        template = template.replace("<*>/<*>", "<*>")

    while "<*>@<*>" in template:
        template = template.replace("<*>@<*>", "<*>")

    while "<*>.<*>" in template:
        template = template.replace("<*>.<*>", "<*>")

    while ' "<*>" ' in template:
        template = template.replace(' "<*>" ', ' <*> ')

    while " '<*>' " in template:
        template = template.replace(" '<*>' ", " <*> ")

    while "<*><*>" in template:
        template = template.replace("<*><*>", "<*>")

    template = re.sub(r'<\*> [KGTM]?B\b', '<*>', template)

    return template

