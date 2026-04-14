from collections import defaultdict
from typing import Dict, List, Any, Tuple, TypedDict
import regex
import re

from detectmatelibrary.common._config._formats import (
    EventsConfig, _EventConfig, _EventInstance, Variable
)
from detectmatelibrary.constants import EVENT_ID


class TemplateMetadata(TypedDict):
    event_id_label: str | None
    labels: list[str]


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
        metadata: dict[int, TemplateMetadata] | None = None,
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

        _metadata: dict[int, TemplateMetadata] = metadata or {}
        self._event_label_to_idx: dict[str, int] = {
            m["event_id_label"]: i
            for i, m in _metadata.items()
            if m["event_id_label"]
        }
        self._idx_to_var_map: dict[int, dict[str, int]] = {
            i: {label: pos for pos, label in enumerate(m["labels"])}
            for i, m in _metadata.items()
            if m["labels"]
        }

    def compile_events_config(self, events_config: EventsConfig) -> EventsConfig:
        """Resolve named event IDs and named variable labels to positional
        ints.

        Translates user-friendly named format to the internal positional
        representation. Returns a new EventsConfig with only int keys
        and int positions.
        """
        new_events: Dict[Any, _EventConfig] = {}

        for event_key, event_config in events_config.events.items():
            if isinstance(event_key, str) and event_key in self._event_label_to_idx:
                resolved_key: str | int = self._event_label_to_idx[event_key]
            else:
                resolved_key = event_key

            var_map = self._idx_to_var_map.get(resolved_key if isinstance(resolved_key, int) else -1, {})

            new_instances: Dict[str, _EventInstance] = {}
            for instance_id, instance in event_config.instances.items():
                new_vars: Dict[str | int, Variable] = {}
                for pos, var in instance.variables.items():
                    if isinstance(pos, str):
                        if pos not in var_map:
                            raise ValueError(
                                f"Label '{pos}' not found in template for event '{event_key}'. "
                                f"Available labels: {list(var_map)}"
                            )
                        resolved_pos = var_map[pos]
                        new_vars[resolved_pos] = Variable(
                            pos=resolved_pos, name=pos, params=var.params
                        )
                    else:
                        new_vars[pos] = var
                new_instances[instance_id] = _EventInstance(
                    params=instance.params,
                    variables=new_vars,
                    header_variables=instance.header_variables,
                )
            new_events[resolved_key] = _EventConfig(instances=new_instances)

        return EventsConfig(events=new_events)

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
        metadata: dict[int, TemplateMetadata] | None = None,
        remove_spaces: bool = True,
        remove_punctuation: bool = True,
        lowercase: bool = True
    ) -> None:
        self.manager = TemplatesManager(
            template_list=template_list,
            metadata=metadata,
            remove_spaces=remove_spaces,
            remove_punctuation=remove_punctuation,
            lowercase=lowercase
        )

    def compile_detector_config(self, events_config: EventsConfig) -> EventsConfig:
        """Resolve named event IDs and variable labels to positional ints.

        Call once at setup time. Returns a new EventsConfig using the
        internal positional representation, compatible with
        get_configured_variables().
        """
        return self.manager.compile_events_config(events_config)

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
        output[EVENT_ID] = tpl_to_id.get(tpl, -1) if output["EventTemplate"] != "<Not Found>" else -1
        return output
