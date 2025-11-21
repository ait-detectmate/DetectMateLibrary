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
            text = text.replace(" ", "")

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
            tokens = cleaned_tpl.split("<*>")
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
        log = re.sub(r'\s+', ' ', log.strip()) # DS
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

    def match_template_with_params(self, log: str) -> tuple[str, tuple[str, ...]] | None:
        """Return (template_string, [param1, param2, ...]) or None."""
        s, candidates = self.manager.candidate_indices(log)
        for i in candidates:
            t = self.manager.templates[i]
            if len(s) < t["min_len"]:
                continue
            params = self.extract_parameters(log, t["raw"])
            if params is not None:
                t["count"] += 1
                return t["raw"], params
        return None

    def __call__(self, log: str) -> Dict[str, Any]:
        """Batch matching that also returns the params list."""
        output = {}
        res = self.match_template_with_params(log)
        if res is None:
            output["EventTemplate"] = "<Not Found>"
            output["Params"] = []  # type: ignore
        else:
            tpl, params = res
            output["EventTemplate"] = tpl
            output["Params"] = params  # type: ignore
        tpl_to_id = {t["raw"]: i for i, t in enumerate(self.manager.templates)}
        output["EventId"] = tpl_to_id.get(tpl, -1) if output["EventTemplate"] != "<Not Found>" else -1  # type: ignore
        return output
