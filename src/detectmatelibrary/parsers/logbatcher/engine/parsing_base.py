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
#
# Changes from original (parsing_base_old.py):
# - Returns a result dict (logs_df, templates_df, cache, metrics, template_samples)
#   instead of writing CSV/JSON files directly to disk.
# - Replaced print() calls with structured logger (tools.logging.logger).
# - Made `cache` an optional parameter to support reuse across calls.
# - Added _extract_template_samples() helper to extract template→sample-log mappings.
# - Default chunk_size raised from 10 000 to 30 000.

import time
import pandas as pd
from collections import Counter
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from tools.logging import logger
from .vars import vars_update
from .cluster import Cluster,tokenize, vectorize, cluster, reassign_clusters, process_new_cluster
from .additional_cluster import hierichical_clustering,meanshift_clustering
from .util import verify_template
from .parsing_cache import ParsingCache

def _extract_template_samples(cache: ParsingCache) -> Dict[str, str]:
    """Extract template to sample log mapping from cache.
    
    Args:
        cache: ParsingCache instance containing template_tree
        
    Returns:
        Dictionary mapping template strings to their sample logs
    """
    template_samples = {}
    
    def traverse_tree(node):
        """Recursively traverse template tree to find all templates."""
        for key, value in node.items():
            if isinstance(value, tuple):
                # Tuple structure: (stat_len, wildcard_count, template, template_id, refer_log)
                template = value[2]  # event_template
                refer_log = value[4]  # sample log
                template_samples[template] = refer_log
            elif isinstance(value, dict):
                traverse_tree(value)
    
    traverse_tree(cache.template_tree)
    return template_samples

def single_dataset_parsing(
    dataset: str,
    contents: List[str],
    parser: Any,
    cache: Optional[ParsingCache] = None,
    batch_size: int = 10,  # number of logs that can be sent to LLM at once
    chunk_size: int = 30000,
    clustering_method: str = 'dbscan',
    debug: bool = True
) -> Dict[str, Any]:
    """Parse logs using clustering and LLM-based template extraction.
    
    Args:
        dataset: Name of the dataset being parsed
        contents: List of log messages to parse
        parser: Parser object with get_responce method
        cache: Optional ParsingCache instance for template caching
        batch_size: Size of batches for processing clusters
        chunk_size: Number of logs to process in each chunk
        clustering_method: Method for clustering ('dbscan', 'hierarchical', or 'meanshift')
        debug: Enable debug logging
        
    Returns:
        Dictionary containing:
            - logs_df: DataFrame with Content and EventTemplate columns
            - templates_df: DataFrame with EventId, EventTemplate, and Occurrence columns
            - cache: Updated ParsingCache instance
            - metrics: Dictionary with parsing statistics
            - template_samples: Dictionary mapping templates to sample logs
    """
    if cache is None:
        cache = ParsingCache()
    
    logs = contents
    log_chunk: List[str] = []
    log_chunk_index: List[int] = []
    
    logger.info(f'Parsing {len(logs)} logs in dataset {dataset}...')

    outputs: List[Optional[str]] = [None for _ in range(len(logs))]
    outputs_index: List[Optional[int]] = [None for _ in range(len(logs))]
    
    # Parsing
    t1 = time.time()
    iterable = tqdm(enumerate(logs), total=len(logs), unit="log")
    for index, log in iterable:

        match_results = cache.match_event(log)
        if match_results[0] != "NoMatch":
            # outputs[index] = match_results[0]
            outputs_index[index] = match_results[1]
        else:
            log_chunk.append(log)
            log_chunk_index.append(index)
        

        # Parsing with LLM
        if len(log_chunk) == chunk_size or (len(log_chunk)!=0 and index == len(logs) - 1):
            # parsing start
            if debug:
                logger.debug(f'Parsing {len(log_chunk)} logs...')
            if clustering_method == 'dbscan':
                # tokenize -> vectorize -> cluster -> reassign_clusters
                tokenized_logs = [tokenize(log) for log in log_chunk]
                labels, cluster_nums = cluster(vectorize(tokenized_logs))
                labels, cluster_nums = reassign_clusters(labels, cluster_nums, tokenized_logs)
            elif clustering_method == 'hierarchical':
                labels, cluster_nums = hierichical_clustering(log_chunk)
            elif clustering_method == 'meanshift':
                labels, cluster_nums = meanshift_clustering(log_chunk)
            else:
                raise ValueError('Invalid clustering method')

            # create clusters
            clusters: List[Optional[Cluster]] = [None for _ in range(cluster_nums)]
            for i, label in enumerate(labels):
                if clusters[label] is None:
                    clusters[label] = Cluster()
                clusters[label].append_log(log_chunk[i], log_chunk_index[i])

            # sorting
            clusters = sorted(clusters, key=lambda cluster: len(cluster.logs), reverse=True)

            # batching
            [cluster.batching(batch_size) for cluster in clusters]

            # parsing
            # print(len(clusters), 'clusters identified') if debug else None  
            for index, old_cluster in enumerate(clusters):
                template, old_cluster, new_cluster = parser.get_responce(old_cluster, cache_base = cache)
                # update clusters
                cluster_nums += process_new_cluster(new_cluster, clusters, batch_size)
                refer_log = old_cluster.logs[0]
                if template not in cache.template_list:
                    if verify_template(template):
                        if debug:
                            logger.debug('=' * 20)
                            logger.debug(f'New cluster processed, {len(set(cache.template_list))} templates identified till now:')
                            logger.debug(f'Refer Log: {refer_log}')
                            logger.debug(f'Output Template: {template}')
                        id, _, _ = cache.add_templates(event_template=template, insert=False, refer_log = refer_log)
                        cache.variable_candidates.extend(vars_update(refer_log, template, cache.variable_candidates))
                    else:
                        id, _, _ = cache.add_templates(event_template=refer_log, insert=False, refer_log = refer_log)
                else:
                    id = cache.template_list.index(template)
                for index in old_cluster.indexs:
                    outputs_index[index] = id
            log_chunk = []
            log_chunk_index = []
    
    outputs = [cache.template_list[i] for i in outputs_index]
    t2 = time.time()
    parsing_time = t2 - t1
    template_count = len(set(outputs))
    
    logger.info(f'Parsing complete: {parsing_time:.3f}s, {template_count} unique templates identified')

    # Create structured logs DataFrame
    logs_df = pd.DataFrame({'Content': logs, 'EventTemplate': outputs})

    # Create templates DataFrame
    counter = Counter(outputs)
    items = list(counter.items())
    items.sort(key=lambda x: x[1], reverse=True)
    templates_df = pd.DataFrame(items, columns=['EventTemplate', 'Occurrence'])
    templates_df['EventId'] = [f"E{i + 1}" for i in range(len(templates_df))]
    templates_df = templates_df[['EventId', 'EventTemplate', 'Occurrence']]

    # Extract template-to-sample-log mapping
    template_samples = _extract_template_samples(cache)

    # Collect metrics
    metrics = {
        'dataset': dataset,
        'parsing_time': round(parsing_time, 3),
        'llm_invocation_time': round(parser.time_consumption_llm, 3),
        'cache_hit_num': cache.hit_num,
        'hash_table_size': len(cache.hashing_cache),
        'token_stats': parser.token_list,
        'template_count': template_count,
        'log_count': len(logs)
    }
    
    return {
        'logs_df': logs_df,
        'templates_df': templates_df,
        'cache': cache,
        'metrics': metrics,
        'template_samples': template_samples,
    }