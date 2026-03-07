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

import time
from typing import Dict, List, Tuple

from openai import OpenAI
# from together import Together
from tenacity import retry, stop_after_attempt, wait_random_exponential
from tools.logging import logger
from .cluster import Cluster
from .postprocess import post_process
from .matching import prune_from_cluster
from .postprocess import correct_single_template
from .util import verify_template, count_message_tokens
from .parsing_cache import ParsingCache

class Parser:

    def __init__(self, model: str, theme: str, config: Dict[str, str]) -> None:

        self.model: str = model
        self.theme: str = theme
        self.dataset: str = 'null'
        self.token_list: List[int] = [0, 0]
        self.time_consumption_llm: float = 0
        if config['api_key_from_openai'] == '<OpenAI_API_KEY>' and config['api_key_from_together'] == '<Together_API_KEY>':
            raise ValueError("Please provide your OpenAI API key and Together API key in the config.json file.")
        if 'gpt' in self.model:
            self.api_key = config['api_key_from_openai']
            self.client = OpenAI(
                api_key=self.api_key
            )
        else:
            # self.api_key = config['api_key_from_together']
            # self.client = Together(
            #     api_key=self.api_key
            # )
            raise ValueError("Only OpenAI API is supported for now.")

    @retry(wait=wait_random_exponential(min=1, max=8), stop=stop_after_attempt(10))
    def chat(self, messages: List[Dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.05,
        )
        return response.choices[0].message.content.strip('\n')

    def get_responce(self, cluster: Cluster, cache_base: ParsingCache) -> Tuple[str, Cluster, Cluster]:

        # initialize
        logs = cluster.batch_logs
        sample_log = cluster.sample_log
        
        # Matching and Pruning
        new_cluster = Cluster()
        for log in cluster.logs:
            template, _, _ = cache_base.match_event(log)
            if template != "NoMatch":
                cluster, new_cluster = prune_from_cluster(
                    template, cluster)
                if new_cluster.size >= 0 and new_cluster.size < cluster.size:
                    return template, cluster, new_cluster
                elif new_cluster.size == cluster.size:
                    cluster.logs, cluster.indexs = new_cluster.logs, new_cluster.indexs
                    new_cluster = Cluster()

        # historical variables
        variable_cluster = Cluster()
        variable_cluster.logs = cache_base.variable_candidates
        if variable_cluster.logs != []:
            variable_cluster.varaible_sampling(5)
        variables = variable_cluster.batch_logs

        variable_prompt = f' Historical variables: {variables}.' if variables != [] else ''
        instruction = "You will be provided with some log messages separated by line break. You must abstract variables with `{{placeholders}}` to extract the corresponding template. The variable type in log messages can be any of the following: ['url', 'IPv4_port', 'host_port', 'package_host', 'IPv6', 'Mac_address', 'time', 'path', 'id', 'date', 'duration', 'size', 'numerical', 'weekday_months', 'user_name']." + variable_prompt + " Constant text and strings should not be recognized as variables.\nPrint the input log's template delimited by backticks."

        # invoke LLM
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": '\n'.join(f'Log[{i+1}]: `{log}`' for i, log in enumerate(logs))}
        ]
        try:
            t0 = time.time()
            answer = self.chat(messages)
            # print(messages)
            # print(answer)
            self.token_list[0] += 1
            self.token_list[1] += count_message_tokens(messages, self.model)
            self.time_consumption_llm += (time.time() - t0)
        except Exception as e:
            logger.error(f"invoke LLM error: {e}")
            answer = sample_log
        
        template = post_process(answer)
        if not verify_template(template):
            template = correct_single_template(sample_log)
        
        cluster, new_cluster = prune_from_cluster(template, cluster)
        if new_cluster.size == cluster.size:
            cluster.logs, cluster.indexs = new_cluster.logs, new_cluster.indexs
            new_cluster = Cluster()
            template = correct_single_template(sample_log)
        return template, cluster, new_cluster
