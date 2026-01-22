from collections import defaultdict
from typing import Dict, List, Any, Tuple
import regex
import re


def safe_search(pattern: str, string: str, timeout: int = 1) -> regex.Match[str] | None:
    """Perform regex search with a timeout to prevent catastrophic
    backtracking."""
    try:
        result = regex.search(pattern, string, timeout=timeout)
    except TimeoutError:
        result = None
    return result


def tokenize_template(string: str) -> List[str]:
    """Split template string treating <*> as tokens."""
    # Split by <*> but keep <*> in the result, then filter empty strings
    return [token for token in re.split(r'(<\*>)', string) if token]


def exclude_digits(string: str) -> bool:
    """Exclude the digits-domain words from partial constant."""
    pattern = r'\d'
    digits = re.findall(pattern, string)
    if len(digits) == 0 or string[0].isalpha() or any(c.isupper() for c in string):
        return False
    elif len(digits) >= 4:
        return True
    else:
        return len(digits) / len(string) > 0.3


def normalize_spaces(text: str) -> str:
    """Replace consecutive spaces with a single space."""
    return re.sub(r' +', ' ', text)


def correct_single_template(template: str, user_strings: set[str] | None = None) -> str:
    """Apply all rules to process a template.

    DS (Double Space) BL (Boolean) US (User String) DG (Digit) PS (Path-
    like String) WV (Word concatenated with Variable) DV (Dot-separated
    Variables) CV (Consecutive Variables)
    """

    boolean = {'true', 'false'}
    default_strings = {'null', 'root'}  # 'null', 'root', 'admin'
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

    # apply DS
    template = template.strip()
    template = re.sub(r'\s+', ' ', template)

    # apply PS
    p_tokens = re.split('(' + '|'.join(path_delimiters) + ')', template)
    new_p_tokens = []
    for p_token in p_tokens:
        if (
            re.match(r'^(\/[^\/]+)+\/?$', p_token) or
            re.match(r'.*/.*\..*', p_token) or
            re.match(r'^([a-zA-Z0-9-]+\.){3,}[a-z]+$', p_token)
        ):
            p_token = '<*>'  # nosec B105

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
                token = '<*>'  # nosec B105

        # apply DG
        # Note: hexadecimal num also appears a lot in the logs
        # if re.match(r'^\d+$', token) or re.match(r'\b0[xX][0-9a-fA-F]+\b', token):
        #     token = '<*>'
        if exclude_digits(token):
            token = '<*>'  # nosec B105

        # apply WV
        if re.match(r'^[^\s\/]*<\*>[^\s\/]*$', token) or re.match(r'^<\*>.*<\*>$', token):
            token = '<*>'  # nosec B105
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


class Preprocess:
    def __init__(
        self,
        re_spaces: bool = True,
        re_punctuation: bool = True,
        do_lowercase: bool = True
    ) -> None:

        self.__re_spaces = re_spaces
        self.__re_punctuation = re_punctuation
        self.__do_lowercase = do_lowercase

        self._punct_re = re.compile(r'[^\w\s]')
        self._ws_re = re.compile(r'\s+')

    @staticmethod
    def _remove_punctuation(text: str) -> str:
        return re.sub(r'[^\w\s]', '', text)

    @staticmethod
    def _remove_extra_spaces(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _to_lowercase(s: str) -> str:
        return s.lower()

    def __call__(self, text: str) -> str:
        if self.__re_spaces:
            text = normalize_spaces(text)

        if self.__re_punctuation:
            text = text.replace("<*>", "WILDCARD")
            text = self._punct_re.sub('', text)
            text = text.replace("WILDCARD", "<*>")

        text = text.strip()
        if not self.__re_spaces:
            text = self._ws_re.sub(' ', text)

        if self.__do_lowercase:
            text = text.lower()

        return text


class TemplatesManager:
    def __init__(
        self,
        template_list: list[str],
        remove_spaces: bool = True,
        remove_punctuation: bool = True,
        lowercase: bool = True
    ) -> None:
        self.preprocess = Preprocess(
            re_spaces=remove_spaces,
            re_punctuation=remove_punctuation,
            do_lowercase=lowercase
        )

        self.templates: List[Dict[str, Any]] = []
        self._prefix_index = defaultdict(list)  # first literal -> [template_idx]

        event_id = 0
        for tpl in template_list:
            cleaned_tpl = self.preprocess(tpl)
            tokens = tokenize_template(cleaned_tpl)
            min_len = sum(len(t) for t in tokens)  # lower bound to skip impossibles

            info = {
                "raw": tpl,
                "tokens": tokens,
                "min_len": min_len,
                "count": 0,
                "event_id": (event_id := event_id + 1)
            }

            idx = len(self.templates)
            self.templates.append(info)
            first = tokens[0] if tokens else ""
            self._prefix_index[first].append(idx)

    def candidate_indices(self, s: str) -> Tuple[str, List[int]]:
        pre_s = self.preprocess(s)
        candidates = []
        for first, idxs in self._prefix_index.items():
            if first == "" or pre_s.startswith(first):
                candidates.extend(idxs)
        candidates.sort(key=lambda i: -self.templates[i]["count"])  # small heuristic
        return pre_s, candidates


class TemplateMatcher:
    def __init__(
        self,
        template_list: list[str],
        remove_spaces: bool = True,
        remove_punctuation: bool = True,
        lowercase: bool = True
    ) -> None:
        self.manager = TemplatesManager(
            template_list=template_list,
            remove_spaces=remove_spaces,
            remove_punctuation=remove_punctuation,
            lowercase=lowercase
        )

    @staticmethod
    def extract_parameters(log: str, template: str) -> tuple[str, ...] | None:
        """Extract parameters from the log based on the template."""
        log = re.sub(r'\s+', ' ', log.strip())
        pattern_parts = template.split("<*>")
        pattern_parts_escaped = [re.escape(part) for part in pattern_parts]
        regex_pattern = "(.*?)".join(pattern_parts_escaped)
        regex = "^" + regex_pattern + "$"
        # matches = re.search(regex, log)
        matches = safe_search(regex, log, 1)
        if matches:
            groups: tuple[str, ...] = matches.groups()
            return groups
        else:
            return None

    @staticmethod
    def correct_single_template(template: str) -> str:
        """Apply all rules to process a template."""
        return correct_single_template(template)

    def match_template_with_params(self, log: str) -> tuple[str, tuple[str, ...]] | None:
        """Return (template_string, [param1, param2, ...]) or None."""
        for i in range(len(self.manager.templates)):
            t = self.manager.templates[i]
            if len(log) < t["min_len"]:
                continue
            t = self.manager.templates[i]
            preprocessed_log = self.manager.preprocess(log)
            preprocessed_template = self.correct_single_template(self.manager.preprocess(t["raw"]))
            params = self.extract_parameters(preprocessed_log, preprocessed_template)
            if params is not None:
                t["count"] += 1
                return t["raw"], params
        return None

    def __call__(self, log: str) -> Dict[str, Any]:
        """Batch matching that also returns the params list."""
        output: dict[str, Any] = {}
        res = self.match_template_with_params(log)
        if res is None:
            output["EventTemplate"] = "<Not Found>"
            output["Params"] = []
        else:
            tpl, params = res
            output["EventTemplate"] = tpl
            output["Params"] = params
        tpl_to_id = {t["raw"]: i for i, t in enumerate(self.manager.templates)}
        output["EventId"] = tpl_to_id.get(tpl, -1) if output["EventTemplate"] != "<Not Found>" else -1
        return output
