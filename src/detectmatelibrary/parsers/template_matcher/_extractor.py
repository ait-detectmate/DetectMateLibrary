from typing import Any


class ParamExtractor:
    @staticmethod
    def _handle_trivial_cases(s: str, tokens: list[str]) -> list[str] | None | str:
        m = len(tokens)
        if m == 0:
            return [] if s == "" else None
        if m == 1:
            return [] if s == tokens[0] else None
        return "CONTINUE"

    @staticmethod
    def _anchor_start(s: str, tokens: list[str]) -> int | None:
        first = tokens[0]
        if first:
            if not s.startswith(first):
                return None
            return len(first)
        return 0

    @staticmethod
    def _handle_last_token(
        s: str, pos: int, next_tok: str
    ) -> Any:

        if next_tok == "":
            return True, s[pos:], len(s)
        if not s.endswith(next_tok):
            return False, None, None
        last_start = len(s) - len(next_tok)
        if last_start < pos:
            return False, None, None
        return True, s[pos:last_start], last_start + len(next_tok)

    @staticmethod
    def _handle_middle_token(
        s: str, pos: int, next_tok: str
    ) -> Any:

        if next_tok == "":
            return True, "", pos
        idx = s.find(next_tok, pos)
        if idx == -1:
            return False, None, None
        return True, s[pos:idx], idx + len(next_tok)

    @staticmethod
    def extract(s: str, tokens: list[str]) -> list[str] | None | str:
        trivial = ParamExtractor._handle_trivial_cases(s, tokens)
        if trivial != "CONTINUE":
            return trivial

        pos = ParamExtractor._anchor_start(s, tokens)
        if pos is None:
            return None

        params: list[str] = []
        m = len(tokens)

        for j in range(0, m - 1):
            next_tok = tokens[j + 1]

            # last token handling
            if j + 1 == m - 1:
                ok, param, new_pos = ParamExtractor._handle_last_token(s, pos, next_tok)
                if not ok:
                    return None
                params.append(param)
                pos = new_pos
                continue

            # middle tokens
            ok, param, new_pos = ParamExtractor._handle_middle_token(s, pos, next_tok)
            if not ok:
                return None
            params.append(param)
            pos = new_pos

        return params
