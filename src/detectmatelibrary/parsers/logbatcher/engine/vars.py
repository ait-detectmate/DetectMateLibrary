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
from typing import List

from .matching import extract_variables

def vars_update(refer_log: str, template: str, candidates: List[str]) -> List[str]:
    new_variables = extract_variables(refer_log, template)
    extend_vars = []
    if not new_variables:
        return extend_vars
    for var in new_variables:
        var = re.sub(r'^\((.*)\)$|^\[(.*)\]$', r'\1\2', var)
        if var not in candidates and not var.isdigit() and not var.isalpha() and len(var.split()) <= 3:
            extend_vars.append(var)
    return extend_vars