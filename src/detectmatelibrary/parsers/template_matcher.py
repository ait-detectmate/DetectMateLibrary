from collections import defaultdict
from functools import lru_cache
import pandas as pd
import re


class TemplateMatcher:
    def __init__(self, template_list: list[str], remove_spaces=True, remove_punctuation=True, lowercase=True):
        self.remove_spaces = remove_spaces
        self.remove_punctuation = remove_punctuation
        self.lowercase = lowercase

        # precompiled regexes for cleaning
        self._punct_re = re.compile(r'[^\w\s]')   # remove punctuation except whitespace
        self._ws_re = re.compile(r'\s+')

        # store templates as: dict(raw, tokens, min_len, count)
        self.templates = []
        self._prefix_index = defaultdict(list)  # first literal -> [template_idx]

        event_id = 0
        for tpl in template_list:
            cleaned_tpl = self._preprocess(tpl)
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

    def _preprocess(self, s: str) -> str:
        # preserve wildcard through cleaning
        if self.remove_spaces:
            s = s.replace(" ", "")
        if self.remove_punctuation:
            s = s.replace("<*>", "WILDCARD")
            s = self._punct_re.sub('', s)
            s = s.replace("WILDCARD", "<*>")
        s = s.strip()
        if not self.remove_spaces:
            s = self._ws_re.sub(' ', s)
        if self.lowercase:
            s = s.lower()
        return s

    @lru_cache(maxsize=100_000)
    def _clean_log_cached(self, log: str) -> str:
        return self._preprocess(log)

    def _candidate_indices(self, s: str):
        # Try buckets whose first literal is a prefix of s, plus the empty-first bucket.
        candidates = []
        for first, idxs in self._prefix_index.items():
            if first == "" or s.startswith(first):
                candidates.extend(idxs)
        candidates.sort(key=lambda i: -self.templates[i]["count"])  # small heuristic
        return candidates

    # ---------- matching with extraction ----------
    @staticmethod
    def _extract_params_if_match(s: str, tokens: list[str]) -> list[str] | None:
        """If 's' matches tokens separated by wildcards, return params captured
        at each <*>.

        Enforces ^...$ semantics. Returns None on mismatch.
        """
        m = len(tokens)
        if m == 0:
            return [] if s == "" else None
        if m == 1:
            return [] if s == tokens[0] else None

        pos = 0
        params: list[str] = []

        # first token must anchor start if non-empty
        if tokens[0]:
            if not s.startswith(tokens[0]):
                return None
            pos = len(tokens[0])

        # iterate over each wildcard position between token j and j+1
        for j in range(0, m - 1):
            cur_tok = tokens[j]
            next_tok = tokens[j + 1]

            if j == 0 and not cur_tok:
                # starting <*>: capture up to the first occurrence of next_tok (or end if it's last and empty)
                pass  # handled uniformly by the logic below

            # last token case
            if j + 1 == m - 1:
                if next_tok == "":  # trailing wildcard
                    params.append(s[pos:])  # capture rest
                    pos = len(s)
                else:
                    if not s.endswith(next_tok):
                        return None
                    last_start = len(s) - len(next_tok)
                    if last_start < pos:
                        return None
                    params.append(s[pos:last_start])
                    pos = last_start + len(next_tok)
                continue

            # middle tokens: find next_tok after current pos (empty next_tok => zero-length)
            if next_tok == "":
                idx = pos
            else:
                idx = s.find(next_tok, pos)
                if idx == -1:
                    return None
            params.append(s[pos:idx])
            pos = idx + len(next_tok)

        # If we get here, anchors are satisfied
        return params

    # ---------- public API ----------
    def match_template(self, log: str) -> str | None:
        """Backwards-compatible: just return the matching template string (or None)."""
        s = self._clean_log_cached(log)
        for i in self._candidate_indices(s):
            t = self.templates[i]
            if len(s) < t["min_len"]:
                continue
            params = self._extract_params_if_match(s, t["tokens"])
            if params is not None:
                t["count"] += 1
                return t["raw"]
        return None

    def match_template_with_params(self, log: str) -> tuple[str, list[str]] | None:
        """Return (template_string, [param1, param2, ...]) or None."""
        s = self._clean_log_cached(log)
        for i in self._candidate_indices(s):
            t = self.templates[i]
            if len(s) < t["min_len"]:
                continue
            params = self._extract_params_if_match(s, t["tokens"])
            if params is not None:
                t["count"] += 1
                return t["raw"], params
        return None

    def match_template_with_params_ids(self, log: str) -> tuple[str, list[str]] | None:
        """Return (template_string, [param1, param2, ...]) or None."""
        s = self._clean_log_cached(log)
        for i in self._candidate_indices(s):
            t = self.templates[i]
            if len(s) < t["min_len"]:
                continue
            params = self._extract_params_if_match(s, t["tokens"])
            if params is not None:
                t["count"] += 1
                return t["raw"], params, t["event_id"]
        return None

    def match_logs(self, data: pd.DataFrame) -> pd.DataFrame:
        """Backwards-compatible batch matching (template only)."""
        df = data.copy()
        df["EventTemplate"] = [self.match_template(x) for x in df["Content"]]
        return df

    def match_logs_with_params(self, data: pd.DataFrame, add_event_id: bool = True) -> pd.DataFrame:
        """Batch matching that also returns the params list."""
        df = data.copy()
        out_tpl = []
        out_params = []
        for x in df["Content"]:
            res = self.match_template_with_params(x)
            if res is None:
                out_tpl.append(None)
                out_params.append(None)
            else:
                tpl, params = res
                out_tpl.append(tpl)
                out_params.append(params)
        df["EventTemplate"] = out_tpl
        df["Params"] = out_params
        if add_event_id:
            tpl_to_id = {t["raw"]: i for i, t in enumerate(self.templates)}
            df["EventId"] = [tpl_to_id.get(tpl, -1) if tpl is not None else -1 for tpl in out_tpl]
        return df
