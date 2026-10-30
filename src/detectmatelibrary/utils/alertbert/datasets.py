from __future__ import annotations

import copy
from collections.abc import Iterable, Iterator
from queue import Empty, PriorityQueue
from typing import Any, Optional, cast

import numpy as np
import torch
from torch.utils.data import BatchSampler, Dataset, Sampler

from detectmatelibrary.schemas import DetectorSchema


def split_alert_dataset(
    dataset: AlertDataset,
    train_val_test_split: tuple[float, float, float] = (0.8, 0.1, 0.1),
    drop_first_n: int = 0,
) -> tuple[AlertDataset, AlertDataset, AlertDataset]:
    """Split an AlertDataset into train, validation and test datasets.

    Args:
        dataset (AlertDataset): The dataset to split.
        train_val_test_split (tuple[float, float, float], optional): The split ratios for train,
            validation and test datasets. Defaults to (0.8, 0.1, 0.1).
        drop_first_n (int, optional): The number of samples to drop from the beginning of the dataset.
            Defaults to 0.

    Returns:
        tuple[AlertDataset, AlertDataset, AlertDataset]: The train, validation and test datasets.
    """
    dataset_length = len(dataset) - drop_first_n
    if not sum(train_val_test_split) == 1.0:
        raise ValueError("train_val_test_split must sum to 1.0")
    train_end = int(dataset_length * train_val_test_split[0]) + drop_first_n
    val_end = train_end + int(dataset_length * train_val_test_split[1])
    train_dataset = copy.deepcopy(dataset)
    train_dataset.data = {
        k: v[drop_first_n:train_end] for k, v in train_dataset.data.items()
    }
    val_dataset = copy.deepcopy(dataset)
    val_dataset.data = {k: v[train_end:val_end] for k, v in val_dataset.data.items()}
    test_dataset = copy.deepcopy(dataset)
    test_dataset.data = {k: v[val_end:] for k, v in test_dataset.data.items()}
    return train_dataset, val_dataset, test_dataset


def detectorschema_to_dict(alert: DetectorSchema) -> dict[str, Any]:
    """Convert a DetectorSchema object to a dictionary and flatten any nested
    ScalarMapContainer objects.

    Args:
        detectorschema (DetectorSchema): The DetectorSchema object to convert.

    Returns:
        dict[str, Any]: The converted dictionary.
    """
    d = alert.as_dict()
    keys = list(d.keys())
    for k in keys:
        if type(d[k]).__name__ == "RepeatedScalarContainer":
            d[k] = list(d[k])
        elif type(d[k]).__name__ == "ScalarMapContainer":
            for sub_k in d[k]:
                d[f"{k}:{sub_k}"] = d[k][sub_k]
            del d[k]
    return d


class MergeAlertSequences:
    """A class for merging multiple alert sequences into a single sequence,
    sorted by timestamp.

    Args:
        sources (dict[str, Iterable[DetectorSchema]]): A dictionary of alert sequences to merge,
        where the keys are the names of the sequences and the values are the sequences themselves.

    Attributes:
        sources (dict[str, Iterable[DetectorSchema]]): A dictionary of alert sequences to merge
        queue (PriorityQueue): A priority queue for merging the alert sequences.

    Methods:
        __iter__(self) -> Iterator[DetectorSchema]: Returns an iterator over the merged alert sequences,
            sorted by timestamp.
        add_source(self, name: str, source: Iterable[DetectorSchema]) -> None: Adds a new alert sequence
            to the merger.
    """

    def __init__(self, sources: dict[str, Iterable[DetectorSchema]]) -> None:
        self.sources = sources
        self.queue: PriorityQueue[tuple[float, str, DetectorSchema]] = PriorityQueue()

        # Initialize the priority queue with the first element from each source
        for name, source in self.sources.items():
            self.add_source(name, source)

    def __iter__(self) -> Iterator[DetectorSchema]:
        while not self.queue.empty():
            try:
                timestamp, name, item = self.queue.get()
                yield item
            except Empty as e:
                raise StopIteration from e
            try:
                next_item = next(iter(self.sources[name]))
                self.queue.put((next_item["logTimestamps"][-1], name, next_item))
            except StopIteration:
                del self.sources[name]

    def add_source(self, name: str, source: Iterable[DetectorSchema]) -> None:
        self.sources[name] = source
        try:
            item = next(iter(source))
            self.queue.put((item["logTimestamps"][-1], name, item))
        except StopIteration:
            del self.sources[name]


class AlertDataset(Dataset[dict[str, Any]]):
    """A dataset class for detectmate alert data. The input is expected to be
    an iterable of detectmate detector schema objects. The input is converted
    to a dictionary of lists, where each key corresponds to a field in the
    detector schema and each value is a list of the corresponding values for
    each alert. Additionally, a new field "relevantTimestamp" is added to each
    alert, which is the last timestamp in the "logTimestamps" field.

    Args:
        source (Iterable[DetectorSchema]): An iterable of detectmate detector schema objects.

    Attributes:
        data (dict[str, list[Any]]): The loaded data.
        keys (dict_keys[str]): The keys of the data.

    Methods:
        process_alert(self, alert: DetectorSchema) -> dict[str, Any]: Processes a single alert and
            returns a dictionary of its fields.
        __len__(self) -> int: Returns the length of the dataset.
        __getitem__(self, idx: int | slice | np.ndarray[int]) -> dict[str, Any] | dict[str, Sequence]:
            Returns the data at the given index or slice. Supports cyclic indexing.
        __iter__(self) -> Iterator[dict[str, Any]]: Returns an iterator over the data.
    """

    def __init__(
        self,
        source: Iterable[DetectorSchema],
    ) -> None:
        super().__init__()

        # load data from all sources
        data = [self.process_alert(alert) for alert in source]
        self.keys = list(set.intersection(*(set(d.keys()) for d in data)))

        # transpose data for faster access
        self.data = {k: [d[k] for d in data] for k in self.keys}

    def process_alert(self, alert: DetectorSchema) -> dict[str, Any]:
        alert_dict = detectorschema_to_dict(alert)
        alert_dict["relevantTimestamp"] = alert_dict["logTimestamps"][-1]
        return alert_dict

    def __len__(self) -> int:
        return len(self.data[self.keys[0]])

    def __getitem__(
        self, idx: int | slice | np.ndarray[int]
    ) -> dict[str, Any] | dict[str, list[Any]]:  # ty: ignore[invalid-method-override]
        if isinstance(idx, int):
            try:
                return {k: self.data[k][idx] for k in self.keys}
            except IndexError:
                idx %= len(self)
                return {k: self.data[k][idx] for k in self.keys}
        elif isinstance(idx, slice):
            start = idx.start if idx.start else 0
            stop = idx.stop if idx.stop else len(self)
            step = idx.step if idx.step else 1
            idx_array = list(range(start, stop, step))
        elif isinstance(idx, np.ndarray):
            idx_array = list(idx)
        else:
            raise TypeError("Index must be an integer, slice or numpy array.")
        if idx_array[0] < 0 or idx_array[-1] >= len(self):
            idx_array = [i % len(self) for i in idx_array]
        return {k: [self.data[k][i] for i in idx_array] for k in self.keys}

    def __iter__(self) -> Iterator[dict[str, Any]]:
        for i in range(len(self)):
            yield {k: self.data[k][i] for k in self.keys}


# alert sequence samplers


class AlertSequenceSampler(Sampler[slice]):
    """A custom PyTorch sampler for sampling sequences from an AlertDataset.

    Args:
        data_source (AlertDataset): The alert dataset to sample from.
        context_size (int, optional): The context window of each sampled sequence. Defaults to 1024.
        cyclic (bool, optional): Whether to sample sequences cyclically. Defaults to False.
        generator (Optional[torch.Generator], optional): The random number generator used for sampling.
            Defaults to None.
        shuffle (bool, optional): Whether to shuffle the sequences. Defaults to True.
            Ignored for time sampling as in time sampling.

    Attributes:
        data_source (AlertDataset): The alert dataset to sample from.
        context_size (int): The size of each sampled sequence.
        cyclic (bool): Whether to sample sequences cyclically.
        shuffle (bool): Whether to shuffle the sequences.
        generator (Optional[torch.Generator]): The random number generator.
        source_length (int): The length of the alert dataset.
        n_chunks (int): The number of chunks in the alert dataset.
        margin (int): The margin for the alert dataset.

    Methods:
        __iter__(self) -> Iterator[slice]: Returns an iterator over the sampled sequences.
            The sampled sequences have randomly chosen offsets.
        __len__(self) -> int: How many times context_size fits in the dataset.
    """

    def __init__(
        self,
        data_source: AlertDataset,
        context_size: int = 1024,
        cyclic: bool = False,
        generator: Optional[torch.Generator] = None,
        shuffle: bool = True,
    ) -> None:
        super().__init__()
        self.data_source = data_source
        self.context_size = context_size
        self.cyclic = cyclic
        self.generator = generator
        self.shuffle = shuffle
        self.source_length = len(data_source)

        # determine how many times context_size fits in each scenario
        self.n_chunks = self.source_length // self.context_size + self.cyclic
        self.margin = self.source_length % self.context_size

    def __iter__(self) -> Iterator[slice[int]]:
        if self.generator is None:
            seed = int(torch.empty((), dtype=torch.int64).random_().item())
            self.generator = torch.Generator()
            self.generator.manual_seed(seed)

        # sample random offsets such that the chunks are different every epoch
        if self.cyclic:
            # we can use any offset
            # offsets are equivalent modulo context_size, hence we can sample
            # them uniformly from [0, context_size)
            offset = torch.randint(
                low=0,
                high=self.context_size,
                size=(1,),
                generator=self.generator,
            )
        else:
            # we need to sample offsets such that the chunks fit in the scenario
            # i.e. we need to sample from [0, margin)
            offset = torch.randint(
                low=0,
                high=self.margin,
                size=(1,),
                generator=self.generator,
            )

        # create a tensor containing the starting indices of the chunks
        index: torch.IntTensor = torch.IntTensor(torch.arange(self.n_chunks) * self.context_size + offset)

        if self.shuffle:
            perm = torch.randperm(len(self), generator=self.generator)
        else:
            perm = torch.tensor(range(len(self)))

        for i in perm:
            yield slice(
                int(index[i].item()),
                int(index[i].item()) + self.context_size,
                1,
            )

    def __len__(self) -> int:
        return self.n_chunks


class AlertSequenceBatchSampler(BatchSampler):
    """A batch sampler for generating batches of sequences from an alert
    dataset.

    Args:
        data_source (AlertDataset): The alert dataset to sample from.
        context_size (int): The size of the context window for each sequence. Defaults to 1024.
        cyclic (bool): Whether to sample sequences in a cyclic manner. Defaults to True.
        generator (torch.Generator | None): The random number generator used for sampling. Defaults to None.
        shuffle (bool): Whether to shuffle the sequences. Defaults to True.
        batch_size (int): The size of each batch. Defaults to 16.
        drop_last (bool): Whether to drop the last incomplete batch. Defaults to True.
    """

    def __init__(
        self,
        data_source: AlertDataset,
        context_size: int = 1024,
        cyclic: bool = True,
        generator: Optional[torch.Generator] = None,
        shuffle: bool = True,
        batch_size: int = 16,
        drop_last: bool = True,
    ) -> None:
        super().__init__(
            cast(
                Sampler[int],
                AlertSequenceSampler(data_source, context_size, cyclic, generator, shuffle),
            ),
            batch_size,
            drop_last,
        )
