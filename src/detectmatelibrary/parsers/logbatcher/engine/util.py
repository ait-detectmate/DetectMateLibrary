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

import re
import string
from typing import Dict, List, Tuple

import pandas as pd
import tiktoken

def data_loader(file_name: str, dataset_format: str, file_format: str) -> List[str]:
    if file_format == 'structured':
        df = pd.read_csv(file_name)
        contents = df['Content'].tolist()
    elif file_format == 'raw':
        with open(file_name, 'r') as f:
            log_raws = f.readlines()
        print(f"Total log lines: {len(log_raws)}")
        headers, regex = generate_logformat_regex(dataset_format)
        contents = log_to_dataframe(file_name, regex, headers, len(log_raws))
    return contents


def count_prompt_tokens(prompt: str, model_name: str) -> int:
    """
    Count the number of tokens in the prompt
    Models supported: gpt-4o-mini, gpt-3.5-turbo
    """
    if model_name == 'gpt-4o-mini':
        encoder = tiktoken.encoding_for_model('gpt-4o-mini')
    elif model_name == 'gpt-3.5-turbo':
        encoder = tiktoken.encoding_for_model('gpt-3.5-turbo')
    else:
        raise ValueError("Unsupported model: {}".format(model_name))

    # 计算编码后的token数
    prompt_tokens = encoder.encode(prompt)
    return len(prompt_tokens)


def count_message_tokens(messages: List[Dict[str, str]], model_name: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in the messages
    Models supported: gpt-4o-mini, gpt-3.5-turbo
    """
    if model_name == 'gpt-4o-mini':
        encoder = tiktoken.encoding_for_model('gpt-4o-mini')
    elif model_name == 'gpt-3.5-turbo':
        encoder = tiktoken.encoding_for_model('gpt-3.5-turbo')
    else:
        raise ValueError("Unsupported model: {}".format(model_name))

    token_count = 0

    for message in messages:
        role_tokens = encoder.encode(message['role'])
        content_tokens = encoder.encode(message['content'])
        token_count += len(role_tokens) + len(content_tokens) + 4
    return token_count


def generate_logformat_regex(logformat: str) -> Tuple[List[str], str]:
        """ 
        Function to generate regular expression to split log messages
        Args:
            logformat: log format, a string
        Returns:
            headers: headers of log messages
            regex: regular expression to split log messages
        """
        headers = []
        splitters = re.split(r'(<[^<>]+>)', logformat)
        regex = ''
        for k in range(len(splitters)):
            if k % 2 == 0:
                splitter = re.sub(' +', r'\\s+', splitters[k])
                regex += splitter
            else:
                header = splitters[k].strip('<').strip('>')
                regex += '(?P<%s>.*?)' % header
                headers.append(header)
        pattern = '^' + regex + '$'
        return headers, pattern


def log_to_dataframe(log_file: str, regex: str, headers: List[str], size: int) -> List[str]:
        """ 
        Function to transform log file to contents
        Args:
            log_file: log file path
            regex: regular expression to split log messages
            headers: headers of log messages
            size: number of log messages to read
        Returns:
            log_messages: list of log contents
        """
        log_contents = []
        with open(log_file, 'r') as file:
            for line in [next(file) for _ in range(size)]:
                try:
                    if not headers:  # If no headers are defined
                        log_contents.append(line.strip())
                        continue
                    match = regex.search(line.strip())
                    message = [match.group(header) for header in headers]
                    log_contents.append(message[-1])
                except Exception as e:
                    pass
        return log_contents


def not_varibility(logs: List[str]) -> bool:
    a_logs = [re.sub(r'\d+', '', log) for log in logs]
    if len(set(a_logs)) == 1:
        return True
    return False

def verify_template(template: str) -> bool:
    template = template.replace("<*>", "")
    template = template.replace(" ", "")
    return any(char not in string.punctuation for char in template)

if __name__ == "__main__":
    import json
    import csv

    # LogBacther
    with open('/root/LogBatcher/messages.json', 'r') as file:
        messages_dict = json.load(file)
    data = []
    datasets = ['BGL', 'HDFS', 'OpenStack', 'OpenSSH', 'HPC', 'Zookeeper', 'Spark', 'Proxifier', 'HealthApp', 'Mac', 'Hadoop', 'Apache', 'Linux', 'Thunderbird']
    all = 0
    for dataset in datasets:
        messages = messages_dict[dataset]
        count = 0
        for message in messages:
            count += count_message_tokens(message)
        print(f"{dataset}: [{count}, {len(messages)}] -> {count/len(messages).__round__(2)}")
        data.append([dataset, count, len(messages), (count/len(messages)).__round__(2)])
        all += count
    print(f"all: {all}")
    with open('/root/LogBatcher/output_lilac_0.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Dataset", "Value1", "Value2", "Value3"])  # 写入标题
        for row in data:
            writer.writerow([row[0], row[1], row[2], row[3]])  # 写入数据
