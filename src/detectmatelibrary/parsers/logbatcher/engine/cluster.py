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

from collections import OrderedDict
import re
from typing import List, Optional, Tuple

import numpy as np
from scipy.sparse import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
from .sample import group_samples_clustering, dpp_sample
from .util import not_varibility
import random
class Cluster:
    def __init__(self) -> None:
        self.logs: List[str] = []
        self.batch_logs: List[str] = []
        self.indexs: List[int] = []
        self.size: int = 0
        self.sample_log: str = ''
        

    def append_log(self, log: str, index: int) -> None:
        self.logs.append(log)
        self.indexs.append(index)
        self.size += 1

    def varaible_sampling(self, batch_size: int = 5, sample_method: str = "dpp") -> None:
        self.batch_logs = list(OrderedDict.fromkeys(self.logs)) # remove duplicates
        def _replacer(match: re.Match[str]) -> str:
            char = match.group()
            return '0' if char.isdigit() else 'a'
        vars = []
        for var in self.batch_logs:
            vars.append(re.sub(r'[0-9a-zA-Z]', _replacer, var))
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform(vars)
            tfidf_matrix = tfidf_matrix.toarray()
        except Exception as e:
            print("VARS", vars)
            raise ValueError("Error during TF-IDF vectorization:", e)

        # sample
        if len(self.batch_logs) <= batch_size:
            result = range(len(self.batch_logs))
        elif sample_method == "dpp":
            similarity_matrix = cosine_similarity(tfidf_matrix)
            result = dpp_sample(similarity_matrix, batch_size)
        elif sample_method == "random":
            random.seed(0)
            result = random.sample(range(0, len(self.batch_logs)), batch_size)
        elif sample_method == "similar":
            result = group_samples_clustering(tfidf_matrix, batch_size)[0]
        else:
            raise ValueError("Invalid sample method")
        self.batch_logs = [self.batch_logs[i] for i in result]

    def batching(self, batch_size: int = 10, min_size: int = 3, sample_method: str = "dpp") -> None:
        self.batch_logs = list(OrderedDict.fromkeys(self.logs)) # remove duplicates
        if len(self.batch_logs) > batch_size:
            self.sample(batch_size, sample_method)
        if type(self.batch_logs) == str:
            self.batch_logs = [self.batch_logs]
        self.sample_log = self.batch_logs[0]
        if not_varibility(self.batch_logs):
            self.batch_logs = self.batch_logs[:min_size] if len(self.batch_logs) > min_size else self.batch_logs

    def sample(self, batch_size: int, sample_method: str) -> None:
        # vetorize logs
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(self.batch_logs)
        tfidf_matrix = tfidf_matrix.toarray()

        # sample
        if sample_method == "dpp":
            similarity_matrix = cosine_similarity(tfidf_matrix)
            result = dpp_sample(similarity_matrix, batch_size)
        elif sample_method == "random":
            random.seed(0)
            result = random.sample(range(0, len(self.batch_logs)), batch_size)
        elif sample_method == "similar":
            result = group_samples_clustering(tfidf_matrix, batch_size)[0]
        else:
            raise ValueError("Invalid sample method")
        self.batch_logs = [self.batch_logs[i] for i in result]
        return

def tokenize(log_content: str, tokenize_pattern: str = r'[ ,|]', removeDight: bool = True) -> List[str]:
    words = re.split(tokenize_pattern, log_content)
    new_words = []
    for word in words:
        if '=' in word:
            ws = word.split('=')
            if len(ws) <= 2:
                new_words.append(ws[0])
            else:
                # might be some parameters of a URL 
                pass 

        elif removeDight and re.search(r'\d', word):
            pass
        elif '/' in word.lower() or re.match(r"^[a-zA-Z][+-]$|^[+-][a-zA-Z]$", word):
            pass
        else:
            word = re.sub(r"\([^)]*\)", "", word)
            new_words.append(word)
    new_words = [word for word in new_words if word]   # remove null
    if new_words == []:
        new_words.append(re.sub(r'\d+(\.\d+)?', '0', log_content))
    return new_words


def vectorize(tokenized_logs: List[List[str]]) -> spmatrix:
    vectorizer = TfidfVectorizer(tokenizer=lambda x: x, lowercase=False, token_pattern=None)
    return vectorizer.fit_transform(tokenized_logs)


def cluster(vectorized_logs: spmatrix, eps: float = 0.5) -> Tuple[np.ndarray, int]:
    cluster = DBSCAN(eps=eps, min_samples=5)
    cluster.fit(vectorized_logs)
    labels = cluster.labels_
    cluster_nums = max(labels) + 1
    return labels, cluster_nums
    

def reassign_clusters(
    labels: np.ndarray, cluster_nums: int, tokenized_logs: List[List[str]]
) -> Tuple[np.ndarray, int]:
    mergerd_logs = []
    for tokenized_log in tokenized_logs:
        mergerd_logs.append(' '.join(tokenized_log))

    for i in range(len(labels)):
        if labels[i] == -1:
            for j in range(i+1, len(labels)):
                if labels[j] == -1 and mergerd_logs[i] == mergerd_logs[j]:
                    labels[j] = cluster_nums
            labels[i] = cluster_nums
            cluster_nums += 1
    return labels, cluster_nums

def process_new_cluster(
    new_cluster: Cluster, clusters: List[Optional[Cluster]], batch_size: int, min_size: int = 3
) -> int:
    if new_cluster.size != 0:
        new_cluster.batching(batch_size, min_size)
        clusters.append(new_cluster)
        return 1
    return 0