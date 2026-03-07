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

from typing import Any, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random
from sklearn.cluster import KMeans
import numpy as np


def dpp_sample(S: np.ndarray, k: int) -> List[int]:
    # S: similarity matrix
    # k: number of items to sample
    n = S.shape[0]

    # Initialize empty set Y
    Y = set()
    for _ in range(k):
        best_i = -1
        best_p = -1

        for i in range(n):
            if i not in Y:
                # Compute determinant of submatrix
                det_Yi = np.linalg.det(S[np.ix_(list(Y) + [i], list(Y) + [i])])

                # Compute probability of adding i to Y
                p_add = det_Yi / (1 + det_Yi)

                if p_add > best_p:
                    best_p = p_add
                    best_i = i

        # Add best item to Y
        Y.add(best_i)

    return list(Y)


def sample_from_clusters(clusters: List[Any], shot: int = 32) -> List[Tuple[str, str]]:
    clusters = sorted(clusters, key=lambda cluster: len(cluster.indexs), reverse=True)
    # form a random list
    random.seed(0)
    random_int_list = [random.randint(0, 1000) for _ in range(10)]

    sample_clusters = []
    sample_pairs = []
    for cluster in clusters:
        if len(sample_clusters) >= shot:
            break
        if cluster.oracle_template not in [pair[1] for pair in sample_clusters]:
            sample_clusters.append((cluster, cluster.oracle_template))

    for random_int in random_int_list:
        if len(sample_pairs) >= shot:
            break
        for item in sample_clusters:
            length = len(item[0].logs)
            if len(sample_pairs) >= shot:
                break
            else:
                sample_pairs.append((item[0].logs[random_int%length], item[1]))
    return sample_pairs


def nearest_k_pairs_from_log(
    log: str, sample_pairs: List[Tuple[str, str]], k: int
) -> List[Tuple[str, str]]:
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([log] + [pair[0] for pair in sample_pairs])
    similarity_matrix = cosine_similarity(tfidf_matrix)
    similarity = similarity_matrix[0][1:]
    nearest_k_indices = similarity.argsort()[-k:][::-1]
    nearest_k_pairs = [sample_pairs[i] for i in nearest_k_indices]
    return nearest_k_pairs



def group_samples_clustering(embed_matrix: np.ndarray, num_in_batch: int) -> List[List[int]]:
    def _calculate_cos_similarities(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
        num = np.dot(v1, v2.T)
        denom = np.linalg.norm(v1, axis=1).reshape(-1, 1) * \
            np.linalg.norm(v2, axis=1)
        similarity_matrix = num / denom
        similarity_matrix[np.isneginf(similarity_matrix)] = 0
        similarity_matrix = 0.5 + 0.5 * similarity_matrix
        return similarity_matrix

    if embed_matrix.shape[0] % num_in_batch:
        n_clusters = embed_matrix.shape[0] // num_in_batch + 1
    else:
        n_clusters = embed_matrix.shape[0] // num_in_batch

    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=0,
                    n_init="auto").fit(embed_matrix)
    similarity_matrix = _calculate_cos_similarities(
        embed_matrix, kmeans.cluster_centers_)  # [n_samples, n_clusters]
    similarity_rankings = np.argsort(-similarity_matrix, axis=1)
    groups = [[] for _ in range(n_clusters)]
    for sample_idx, label in enumerate(kmeans.labels_):
        groups[label].append(sample_idx)
    # Reassign to equalize the number of samples in each cluster
    for group_idx, group in enumerate(groups):
        if len(group) > num_in_batch:
            groups[group_idx] = sorted(
                group, key=lambda x: similarity_matrix[x, group_idx], reverse=True)
            samples_to_reassign = groups[group_idx][num_in_batch:]
            groups[group_idx] = groups[group_idx][:num_in_batch]
            for sample_idx in samples_to_reassign:
                for candi_group_idx in similarity_rankings[sample_idx]:
                    if len(groups[candi_group_idx]) < num_in_batch:
                        groups[candi_group_idx].append(sample_idx)
                        break
    return groups
