import json
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from typing import Any, Optional

import numpy as np
import torch
from tensordict import TensorDict


class Vocabulary:
    """Vocabulary class for tokenizing sequential data.

    Args:
        min_freq (int): The minimum frequency of a word to be included in the vocabulary. Default is 1.

    Attributes:
        base_vocabulary (list[str]): The base vocabulary containing the special tokens "<MASK>" and "<UNK>".
        min_freq (int): The minimum frequency of a word to be included in the vocabulary.
        counter (Counter[Any]): A counter object that stores the frequencies of words.
        offset (int): The offset of the vocabulary indices due to the base vocabulary being at the beginning
            of the vocabulary. The "<UNK>" token is exempt from this offset as
            it can be predicted by the model.
        vocabulary (list[Any]): The vocabulary containing all words encountered with a frequency greater or
            equal to min_freq.
        word2idx (dict[Any, int]): A dictionary mapping words to their corresponding
            indices in the vocabulary.
        vocab_size (int): The size of the vocabulary.
        num_targets (int): The number of tokens that can be predicted by the model, i.e "<UNK>"
            and the words with more than min_freq occurrences.

    Methods:
        refresh(): Refreshes the vocabulary based on the contents of the counter.
        build_from_iterator(iterator: Iterable[Any]): Builds the vocabulary from an iterator of objects.
        remove(words: Iterable[Any]): Removes specified words from the vocabulary.
            This changes the word2idx mapping!
        get_frequencies() -> torch.FloatTensor: Returns the frequencies of target words in the vocabulary,
            i.e. the returned tensor contains num_targets values and the first value is the frequency of
                "<UNK>" which includes all words with less than min_freq occurrences.
        compute_targets(tokens: torch.IntTensor) -> torch.IntTensor: Computes target indices from tokens.
        __call__(src: str | Sequence[Any]) -> int | torch.IntTensor: To be used as collate function, returns
            the token of a word or a tensor of tokens for a sequence of words.
        save(path: str): Saves the vocabulary to a file.
        load(path: str): Loads the vocabulary from a file.
        __len__() -> int: Returns the size of the vocabulary.
        __getitem__(idx: int) -> Any: Returns the word at the specified index.
        __iter__() -> Iterable[Any]: Returns an iterator over the vocabulary words.
    """

    base_vocabulary = ["<MASK>", "<UNK>"]

    def __init__(self, min_freq: int = 1) -> None:
        self.min_freq = min_freq
        self.counter: Counter[str] = Counter()
        self.offset = len(self.base_vocabulary) - 1
        self.refresh()

    def refresh(self) -> None:
        self.vocabulary = self.base_vocabulary + [
            word for word, freq in self.counter.items() if freq >= self.min_freq
        ]
        self.word2idx = {word: idx for idx, word in enumerate(self.vocabulary)}
        self.vocab_size = len(self.vocabulary)
        self.num_targets = self.vocab_size - self.offset

    def build_from_iterator(self, iterator: Iterable[Any]) -> None:
        self.counter.update(iterator)
        self.refresh()

    def remove(self, words: Iterable[Any]) -> None:
        for word in words:
            del self.counter[word]
        self.refresh()

    def get_frequencies(self) -> torch.FloatTensor:
        total = sum(self.counter.values())
        frequencies = [
            self.counter[word] / total
            for word in self.vocabulary[len(self.base_vocabulary):]
        ]
        # words with less than min_freq occurrences are assigned to <UNK>
        frequencies = [1.0 - sum(frequencies)] + frequencies
        return torch.FloatTensor(frequencies)

    def compute_targets(self, tokens: torch.IntTensor) -> torch.IntTensor:
        return torch.IntTensor(tokens - self.offset)

    def __call__(self, src: str | Sequence[Sequence[str]]) -> int | torch.IntTensor:
        if isinstance(src, str):
            # if called on string return token of word
            # if word is not in vocabulary return token of <UNK>
            return self.word2idx.get(src, self.word2idx["<UNK>"])
        else:
            # if called on sequence of strings return tensor of tokens
            return torch.IntTensor(torch.tensor(
                [[self(token) for token in sequence] for sequence in src],
                dtype=torch.int64,
            ))

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(dict(self.counter.most_common()), f, indent=4)

    def load(self, path: str) -> None:
        with open(path) as f:
            self.counter = Counter(json.load(f))
        self.refresh()

    def __len__(self) -> int:
        return self.vocab_size

    def __getitem__(self, idx: int) -> Any:  # noqa: ANN401
        return self.vocabulary[idx]

    def __iter__(self) -> Iterable[Any]:
        return iter(self.vocabulary)


# collate functions


def default_collate_fn(x: Sequence[np.ndarray]) -> torch.Tensor:
    """Basic collate function that stacks a batch of numpy arrays into a torch
    tensor.

    Args:
        x (Sequence[np.ndarray]): A sequence of numpy arrays to be collated.

    Returns:
        torch.Tensor: A tensor containing the stacked numpy arrays.
    """
    return torch.tensor(np.stack(x))


class BaseSequenceCollate:
    """A class for collating dictionaries of sequences into dictionaries of
    batches.

    Args:
        collate_fn_map (dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]]):
            A dictionary mapping feature names to collate functions that convert a sequence of numpy arrays
            into a torch tensor.
        generator (Optional[torch.Generator]):
            An optional torch generator for random number generation. If not provided,
                a new generator will be created.

    Attributes:
        collate_fn_map (dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]]):
            A dictionary mapping feature names to collate functions that convert a sequence of
                numpy arrays into a torch tensor.
        generator (torch.Generator):
            A torch generator for random number generation.

    Methods:
        __call__(batch: Iterable[dict[str, np.ndarray]]) -> TensorDict[str, torch.Tensor]:
            Collates the input batch of dictionaries of sequences into a dictionary of batches.
    """

    def __init__(
        self,
        collate_fn_map: dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]],
        generator: Optional[torch.Generator] = None,
    ) -> None:
        self.collate_fn_map = collate_fn_map
        self.add_position = "position" in collate_fn_map
        if generator is None:
            seed = int(torch.empty((), dtype=torch.int64).random_().item())
            self.generator = torch.Generator()
            self.generator.manual_seed(seed)
        else:
            self.generator = generator

    def __call__(
        self, batch: Sequence[dict[str, np.ndarray]]
    ) -> TensorDict[str, torch.Tensor]:
        batch_size = len(batch)
        context_size = len(next(iter(batch[0].values())))
        # transpose the batch of feature dictionaries to a dictionary of feature batches
        if self.add_position:
            return_batch: dict[str, list[np.ndarray]] = {
                k: [d[k] for d in batch] for k in self.collate_fn_map if k != "position"
            }
            return_batch["position"] = [np.arange(context_size) for i in range(batch_size)]
        else:
            return_batch = {
                k: [d[k] for d in batch] for k in self.collate_fn_map
            }
        # apply the collate functions to the feature batches and return it as a TensorDict
        return_batch_2: TensorDict[str, torch.Tensor] = TensorDict(
            {k: self.collate_fn_map[k](return_batch[k]) for k in self.collate_fn_map}
        )
        return_batch_2.batch_size_ = (batch_size, context_size)
        return return_batch_2


class MaskedLangModelingSequenceCollate(BaseSequenceCollate):
    """A collate function for training a masked language model on sequential
    data. In an input sequence target_ratio of the tokens will be targets for
    prediction, mask_ratio of the target tokens will be masked, perturb_ratio
    of the masked target tokens will be permuted, and the rest of the target
    tokens will be left unchanged.

    Args:
        collate_fn_map (dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]]):
            A dictionary mapping feature names to collate functions that convert a sequence of numpy
            arrays into a torch tensor.
        target_ratio (float, optional):
            The ratio of tokens that will be targets for prediction. Default is 0.15.
        mask_ratio (float, optional):
            The ratio of target tokens that will be masked. Default is 0.8.
        perturb_ratio (float, optional):
            The ratio of masked target tokens that will be permuted. Default is 0.1.
        generator (Optional[torch.Generator]):
            An optional torch generator for random number generation. If not provided,
            a new generator will be created.

    Methods:
        __call__(batch: Iterable[dict[str, np.ndarray]]) -> TensorDict[str, torch.Tensor]:
            Collates the input batch of dictionaries of sequences into a dictionary of batches and
            applies the RoBERTa-like masking.
    """

    def __init__(
        self,
        collate_fn_map: dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]],
        target_ratio: float = 0.15,
        mask_ratio: float = 0.8,
        perturb_ratio: float = 0.1,
        generator: Optional[torch.Generator] = None,
    ) -> None:
        super().__init__(collate_fn_map, generator)
        self.target_ratio = target_ratio
        self.mask_ratio = mask_ratio
        self.perturb_ratio = perturb_ratio

    def __call__(
        self, batch: Sequence[dict[str, np.ndarray]]
    ) -> TensorDict[str, torch.Tensor]:
        return_batch: TensorDict[str, torch.Tensor] = super().__call__(batch)
        # get batch size and sequence length
        dim = return_batch.batch_size_
        # draw random numbers to define target tokens
        mask = torch.rand(dim, generator=self.generator)
        # self.target_ratio of the tokens will be targets for prediction
        return_batch["mask"] = mask <= self.target_ratio
        # save indices of target tokens
        return_batch["mask_index"] = torch.nonzero(return_batch["mask"]).t()
        # define permutation of self.perturb_ratio of the target tokens within each sequence
        perturb_mask = torch.logical_and(
            (self.target_ratio * self.mask_ratio) < mask,
            mask <= (self.target_ratio * (self.mask_ratio + self.perturb_ratio)),
        )
        idxs = [torch.nonzero(sequence, as_tuple=True) for sequence in perturb_mask]
        perms = [torch.randperm(len(idx[0]), generator=self.generator) for idx in idxs]
        perm_idxs = [
            (i * torch.ones_like(idx[0]), idx[0][perm])
            for i, (idx, perm) in enumerate(zip(idxs, perms))
        ]
        idx = (
            torch.cat([i * torch.ones_like(idx[0]) for i, idx in enumerate(idxs)]),
            torch.cat([idx[0] for idx in idxs]),
        )
        perm_idx = (
            torch.cat([idx[0] for idx in perm_idxs]),
            torch.cat([idx[1] for idx in perm_idxs]),
        )
        for feature in self.collate_fn_map:
            # permutation is applied to features for positional encoding
            if feature in ["position", "raw_time", "time", "relevantTimestamp"]:
                return_batch[feature][idx] = return_batch[feature][perm_idx]
            else:
                # mask self.mask_ratio of the target tokens
                return_batch[f"{feature}_mask"] = return_batch[feature] * (
                    mask > self.target_ratio * self.mask_ratio
                )
        return return_batch
