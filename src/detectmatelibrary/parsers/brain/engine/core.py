# =========================================================================
# Copyright (C) 2016-2023 LOGPAI (https://github.com/logpai).
# Copyright (C) 2023 gaiusyu
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========================================================================
"""Vendored core of Brain (https://github.com/logpai/logparser/tree/main/logparser/Brain).

Ported from ``Brain.py``'s ``LogParser``/``tupletree`` classes. The file-I/O,
CSV, CLI and dataset-loading plumbing (``load_data``, ``generateresult``,
``format_log``, ``save_result``, ``__main__``) has been stripped since this
library streams logs in-memory; the tuple-tree template derivation itself
(``get_frequecy_vector``, ``tuple_generate``, ``tupletree.find_root``,
``tupletree.up_split``, ``tupletree.down_split``, ``output_result``) is kept
faithful to upstream, including its quirks (e.g. the always-false
frequency/tuple comparison in ``up_split``, preserved below with a
``type: ignore`` rather than "fixed", since fixing it would change which
templates Brain derives).
"""

from collections import Counter

import regex as re

Word = str | int
FreqTuple = tuple[int, Word, int]
FreqCountPair = tuple[int, int]

GroupLen = dict[int, list[list[str]]]
TupleVector = dict[int, list[list[FreqTuple]]]
FrequencyVector = dict[int, list[list[int]]]
SortedTupleVector = TupleVector
WordCombinations = dict[int, list[list[FreqCountPair]]]

RootKey = FreqCountPair
RootSetDetailID = dict[RootKey, list[list[FreqTuple]]]
RootSet = dict[RootKey, list[list[FreqCountPair]]]
RootSetDetail = dict[RootKey, list[list[FreqTuple]]]

TemplateSet = dict[tuple[str, ...], list[int]]

_DIGIT_RE = re.compile(r"\d")


def get_frequecy_vector(
    sentences: list[str],
    rex: list[str],
    delimiter: list[str],
    dataset: str = "",
) -> tuple[GroupLen, TupleVector, FrequencyVector]:
    """Preprocess sentences, group by length and convert each log into a
    frequency vector.

    Output:
        group_len: log groups based on length (each entry is [line_id, tok1, tok2, ...])
        tuple_vector: each word converted into (word_frequency, word_character, word_position)
        frequency_vector: each word converted into its frequency
    """
    group_len: GroupLen = {}
    word_positions: dict[str, list[str]] = {}
    for line_id, raw_line in enumerate(sentences):
        s = raw_line
        for rgex in rex:
            s = re.sub(rgex, "<*>", s)
        for de in delimiter:
            s = re.sub(de, "", s)
        # Disabled: the following rules are hand-tuned to the specific
        # benchmark datasets (HealthApp, Android, HDFS, ...). This is a form
        # of overfitting to the benchmark - the parser looks artificially
        # good on exactly these datasets, but its performance no longer says
        # anything about how it does on new, unseen logs. For a fair
        # evaluation of generalization, the preprocessing should be
        # dataset-agnostic. The logic is kept for reference but commented out.

        # if dataset == "HealthApp":
        #     s = re.sub(":", ": ", s)
        #     s = re.sub("=", "= ", s)
        #     s = re.sub(r"\|", "| ", s)
        # if dataset == "Android":
        #     s = re.sub(r"\(", "( ", s)
        #     s = re.sub(r"\)", ") ", s)
        # if dataset == "Android":
        #     s = re.sub(":", ": ", s)
        #     s = re.sub("=", "= ", s)
        # if dataset == "HPC":
        #     s = re.sub("=", "= ", s)
        #     s = re.sub("-", "- ", s)
        #     s = re.sub(":", ": ", s)
        # if dataset == "BGL":
        #     s = re.sub("=", "= ", s)
        #     s = re.sub(r"\.\.", ".. ", s)
        #     s = re.sub(r"\(", "( ", s)
        #     s = re.sub(r"\)", ") ", s)
        # if dataset == "Hadoop":
        #     s = re.sub("_", "_ ", s)
        #     s = re.sub(":", ": ", s)
        #     s = re.sub("=", "= ", s)
        #     s = re.sub(r"\(", "( ", s)
        #     s = re.sub(r"\)", ") ", s)
        # if dataset == "HDFS":
        #     s = re.sub(":", ": ", s)
        # if dataset == "Linux":
        #     s = re.sub("=", "= ", s)
        #     s = re.sub(":", ": ", s)
        # if dataset == "Spark":
        #     s = re.sub(":", ": ", s)
        # if dataset == "Thunderbird":
        #     s = re.sub(":", ": ", s)
        #     s = re.sub("=", "= ", s)
        # if dataset == "Windows":
        #     s = re.sub(":", ": ", s)
        #     s = re.sub("=", "= ", s)
        #     s = re.sub(r"\[", "[ ", s)
        #     s = re.sub("]", "] ", s)
        # if dataset == "Zookeeper":
        #     s = re.sub(":", ": ", s)
        #     s = re.sub("=", "= ", s)
        s = re.sub(",", ", ", s)
        tokens = re.sub(" +", " ", s).split(" ")
        tokens.insert(0, str(line_id))
        for position, token in enumerate(tokens):
            word_positions.setdefault(str(position), []).append(token)
        length = len(tokens)
        group_len.setdefault(length, []).append(tokens)

    tuple_vector: TupleVector = {}
    frequency_vector: FrequencyVector = {}
    if not group_len:
        return group_len, tuple_vector, frequency_vector

    max_length = max(group_len)
    freq_table: dict[str, int] = {}
    for position in range(max_length):
        for word in word_positions[str(position)]:
            key = f"{position} {word}"
            freq_table[key] = freq_table.get(key, 0) + 1

    for length, lines in group_len.items():
        for tokens in lines:
            position = 0
            fre: list[FreqTuple] = []
            fre_common: list[int] = []
            for idx, token in enumerate(tokens):
                if idx == 0:
                    continue  # skip the injected line id
                frequency_word = freq_table[f"{position + 1} {token}"]
                fre.append((frequency_word, token, position))
                fre_common.append(frequency_word)
                position += 1
            tuple_vector.setdefault(length, []).append(fre)
            frequency_vector.setdefault(length, []).append(fre_common)

    return group_len, tuple_vector, frequency_vector


def tuple_generate(
    group_len: GroupLen,
    tuple_vector: TupleVector,
    frequency_vector: FrequencyVector,
) -> tuple[SortedTupleVector, WordCombinations, WordCombinations]:
    """Generate word combinations.

    Output:
        sorted_tuple_vector: each tuple in tuple_vector, sorted by frequency (descending).
        word_combinations: words with the same frequency grouped, descending by frequency.
        word_combinations_reverse: same word combinations, ascending by frequency.
    """
    sorted_tuple_vector: SortedTupleVector = {}
    word_combinations: WordCombinations = {}
    word_combinations_reverse: WordCombinations = {}
    for key in group_len:
        for fre in tuple_vector[key]:
            sorted_fre_reverse = sorted(fre, key=lambda tup: tup[0], reverse=True)
            sorted_tuple_vector.setdefault(key, []).append(sorted_fre_reverse)
        for fc in frequency_vector[key]:
            counted = Counter(fc)
            result = counted.most_common()
            sorted_result = sorted(result, key=lambda tup: tup[1], reverse=True)
            sorted_fre = sorted(result, key=lambda tup: tup[0], reverse=True)
            word_combinations.setdefault(key, []).append(sorted_result)
            word_combinations_reverse.setdefault(key, []).append(sorted_fre)
    return sorted_tuple_vector, word_combinations, word_combinations_reverse


class tupletree:  # lowercase name kept for fidelity with upstream Brain.py
    """tupletree(sorted_tuple_vector[key], word_combinations[key],
    word_combinations_reverse[key], tuple_vector[key], group_len[key])"""

    def __init__(
        self,
        sorted_tuple_vector: list[list[FreqTuple]],
        word_combinations: list[list[FreqCountPair]],
        word_combinations_reverse: list[list[FreqCountPair]],
        tuple_vector: list[list[FreqTuple]],
        group_len: list[list[str]],
    ) -> None:
        self.sorted_tuple_vector = sorted_tuple_vector
        self.word_combinations = word_combinations
        self.word_combinations_reverse = word_combinations_reverse
        self.tuple_vector = tuple_vector
        self.group_len = group_len

    def find_root(
        self, threshold_per: int
    ) -> tuple[RootSetDetailID, RootSet, RootSetDetail]:
        root_set_detail_id: RootSetDetailID = {}
        root_set_detail: RootSetDetail = {}
        root_set: RootSet = {}
        for i, fc in enumerate(self.word_combinations):
            count = self.group_len[i]
            threshold = max(fc, key=lambda tup: tup[0])[0] * threshold_per
            candidate = fc[0]
            m = 0
            for fc_w in fc:
                if fc_w[0] >= threshold:
                    self.sorted_tuple_vector[i].append((int(count[0]), -1, -1))
                    root_set_detail_id.setdefault(fc_w, []).append(
                        self.sorted_tuple_vector[i]
                    )
                    root_set.setdefault(fc_w, []).append(
                        self.word_combinations_reverse[i]
                    )
                    root_set_detail.setdefault(fc_w, []).append(self.tuple_vector[i])
                    break
                if fc_w[0] >= m:
                    candidate = fc_w
                    m = fc_w[0]
                if fc_w == fc[-1]:
                    self.sorted_tuple_vector[i].append((int(count[0]), -1, -1))
                    root_set_detail_id.setdefault(candidate, []).append(
                        self.sorted_tuple_vector[i]
                    )
                    root_set.setdefault(candidate, []).append(
                        self.word_combinations_reverse[i]
                    )
                    root_set_detail.setdefault(fc_w, []).append(self.tuple_vector[i])
        return root_set_detail_id, root_set, root_set_detail

    def up_split(
        self, root_set_detail: RootSetDetailID, root_set: RootSet
    ) -> RootSetDetailID:
        for key in root_set:
            tree_node = root_set[key]
            father_count: list[FreqCountPair] = []
            for node in tree_node:
                pos = node.index(key)
                for i in range(pos):
                    father_count.append(node[i])
            father_set = set(father_count)
            for father in father_set:
                if father_count.count(father) == key[0]:
                    continue
                for i in range(len(root_set_detail[key])):
                    for k in range(len(root_set_detail[key][i])):
                        # Upstream compares an (freq, count) pair to a full
                        # (freq, word, position) tuple here, which is never
                        # equal - so this branch never fires. Kept as-is:
                        # "fixing" it would change which words Brain treats
                        # as constants and diverge from upstream templates.
                        if father[0] == root_set_detail[key][i][k]:  # type: ignore[comparison-overlap]
                            entry = root_set_detail[key][i][k]
                            root_set_detail[key][i][k] = (entry[0], "<*>", entry[2])
                break
        return root_set_detail

    def down_split(
        self,
        root_set_detail_id: RootSetDetailID,
        threshold: int,
        root_set_detail: RootSetDetail,
    ) -> RootSetDetailID:
        for key in root_set_detail_id:
            detail_order = root_set_detail[key]
            m: list[int] = []
            child: dict[int, list[Word]] = {}
            variable: set[Word] = set()
            first_sentence = detail_order[0]
            for m_count, det in enumerate(first_sentence):
                if det[0] != key[0]:
                    m.append(m_count)
            for i in m:
                for node in detail_order:
                    if i < len(node):
                        child.setdefault(i, []).append(node[i][1])
            for i in m:
                result = set(child[i])
                freq = len(result)
                if freq >= threshold:
                    variable = variable.union(result)
            for i, entries in enumerate(root_set_detail_id[key]):
                for j, entry in enumerate(entries):
                    if isinstance(entry, tuple) and entry[1] in variable:
                        root_set_detail_id[key][i][j] = (entry[0], "<*>", entry[2])
        return root_set_detail_id


def output_result(parse_result: dict[RootKey, list[list[FreqTuple]]]) -> TemplateSet:
    template_set: TemplateSet = {}
    for results in parse_result.values():
        for pr in results:
            sorted_pr = sorted(pr, key=lambda tup: tup[2])
            template: list[str] = []
            for entry in sorted_pr[1:]:
                word = entry[1]
                if not isinstance(word, str):
                    continue  # only the (already-skipped) sentinel is an int
                if "<*>" in word:
                    template.append("<*>")
                    continue
                if exclude_digits(word):
                    template.append("<*>")
                    continue
                template.append(word)
            template_set.setdefault(tuple(template), []).append(pr[-1][0])
    return template_set


def exclude_digits(string: str) -> bool:
    """Exclude the digits-domain words from partial constant."""
    digits = _DIGIT_RE.findall(string)
    if not digits:
        return False
    return len(digits) / len(string) >= 0.3


def derive_templates(
    contents: list[str],
    threshold: int = 2,
    delimiter: list[str] | None = None,
    rex: list[str] | None = None,
    dataset: str = "",
) -> list[str]:
    """Run Brain's tuple-tree algorithm over a batch of log contents and return
    the derived template strings (words joined by spaces, variable positions
    marked with ``<*>``)."""
    if not contents:
        return []

    group_len, tuple_vector, frequency_vector = get_frequecy_vector(
        contents, rex or [], delimiter or [], dataset
    )
    sorted_tuple_vector, word_combinations, word_combinations_reverse = tuple_generate(
        group_len, tuple_vector, frequency_vector
    )

    templates: TemplateSet = {}
    for key in group_len:
        tree = tupletree(
            sorted_tuple_vector[key],
            word_combinations[key],
            word_combinations_reverse[key],
            tuple_vector[key],
            group_len[key],
        )
        root_set_detail_id, root_set, root_set_detail = tree.find_root(0)
        root_set_detail_id = tree.up_split(root_set_detail_id, root_set)
        parse_result = tree.down_split(root_set_detail_id, threshold, root_set_detail)
        templates.update(output_result(parse_result))

    return [" ".join(template) for template in templates]


class LogParser:
    """In-memory port of Brain's ``LogParser`` (file I/O stripped).

    Mirrors upstream's constructor knobs (``threshold``, ``delimeter``/
    ``delimiter``, ``rex``) minus the file-path arguments, which have no
    meaning for a streaming, in-memory parser.
    """

    def __init__(
        self,
        threshold: int = 2,
        delimiter: list[str] | None = None,
        rex: list[str] | None = None,
        dataset: str = "",
    ) -> None:
        self.threshold = threshold
        self.delimiter = delimiter or []
        self.rex = rex or []
        self.dataset = dataset

    def parse(self, contents: list[str]) -> list[str]:
        """Derive the Brain template set for a batch of log message
        contents."""
        return derive_templates(
            contents, self.threshold, self.delimiter, self.rex, self.dataset
        )
