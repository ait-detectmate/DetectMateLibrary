import json
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from typing import Any, Optional, cast

import numpy as np
import torch
from tensordict import TensorDict


class Vocabulary:
    """Vocabulary class for tokenizing sequential data.

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
    """

    base_vocabulary = ["<MASK>", "<UNK>"]

    def __init__(self, min_freq: int = 1) -> None:
        """Initialize an empty vocabulary.

        Args:
            min_freq: Minimum frequency required for a word to be included.
        """
        self.min_freq = min_freq
        self.counter: Counter[str] = Counter()
        self.offset = len(self.base_vocabulary) - 1
        self.refresh()

    def refresh(self) -> None:
        """Refresh vocabulary indices and sizes from the word counter."""
        self.vocabulary = self.base_vocabulary + [
            word for word, freq in self.counter.items() if freq >= self.min_freq
        ]
        self.word2idx = {word: idx for idx, word in enumerate(self.vocabulary)}
        self.vocab_size = len(self.vocabulary)
        self.num_targets = self.vocab_size - self.offset

    def build_from_iterator(self, iterator: Iterable[Any]) -> None:
        """Add words from an iterator and refresh the vocabulary.

        Args:
            iterator: Iterable containing words to add to the vocabulary.
        """
        self.counter.update(iterator)
        self.refresh()

    def remove(self, words: Iterable[Any]) -> None:
        """Remove words from the vocabulary and refresh its indices.

        Args:
            words: Iterable containing words to remove.
        """
        for word in words:
            del self.counter[word]
        self.refresh()

    def get_frequencies(self) -> torch.FloatTensor:
        """Return normalized frequencies for all prediction targets.

        Returns:
            A tensor containing the frequency of ``<UNK>`` followed by the
            frequencies of all words included in the vocabulary.
        """
        total = sum(self.counter.values())
        frequencies = [
            self.counter[word] / total
            for word in self.vocabulary[len(self.base_vocabulary):]
        ]
        # words with less than min_freq occurrences are assigned to <UNK>
        frequencies = [1.0 - sum(frequencies)] + frequencies
        return torch.FloatTensor(frequencies)

    def compute_targets(self, tokens: torch.Tensor) -> torch.Tensor:
        """Convert vocabulary tokens to model target indices.

        Args:
            tokens: Tensor containing vocabulary token indices.

        Returns:
            Tensor containing indices relative to the model's target classes.
        """
        return (tokens - self.offset).to(dtype=torch.int64)

    def __call__(self, src: str | Sequence[Sequence[str]]) -> int | torch.IntTensor:
        """Convert a word or sequence of words to vocabulary indices.

        Args:
            src: A word or a sequence of word sequences to tokenize.

        Returns:
            The index of a word, or a tensor of indices for a sequence.
        """
        if isinstance(src, str):
            # if called on string return token of word
            # if word is not in vocabulary return token of <UNK>
            return self.word2idx.get(src, self.word2idx["<UNK>"])
        else:
            # if called on sequence of strings return tensor of tokens
            return cast(
                torch.IntTensor,
                torch.tensor(
                    [[self(token) for token in sequence] for sequence in src],
                    dtype=torch.int64,
                ),
            )

    def save(self, path: str) -> None:
        """Save word frequencies as JSON.

        Args:
            path: Destination path for the vocabulary data.
        """
        with open(path, "w") as f:
            json.dump(dict(self.counter.most_common()), f, indent=4)

    def load(self, path: str) -> None:
        """Load word frequencies from JSON and refresh the vocabulary.

        Args:
            path: Source path containing vocabulary data.
        """
        with open(path) as f:
            self.counter = Counter(json.load(f))
        self.refresh()

    def __len__(self) -> int:
        """Return the number of entries in the vocabulary."""
        return self.vocab_size

    def __getitem__(self, idx: int) -> Any:  # noqa: ANN401
        """Return the vocabulary entry at an index.

        Args:
            idx: Index of the requested vocabulary entry.

        Returns:
            The vocabulary entry at ``idx``.
        """
        return self.vocabulary[idx]

    def __iter__(self) -> Iterable[Any]:
        """Return an iterator over vocabulary entries."""
        return iter(self.vocabulary)


# collate functions


def default_collate_fn(x: Sequence[np.ndarray]) -> torch.Tensor:
    """Stack a batch of NumPy arrays into a tensor.

    Args:
        x: A sequence of NumPy arrays to collate.

    Returns:
        A tensor containing the stacked NumPy arrays.
    """
    return torch.tensor(np.stack(x))


class BaseSequenceCollate:
    """A class for collating dictionaries of sequences into dictionaries of
    batches.

    Attributes:
        collate_fn_map (dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]]):
            A dictionary mapping feature names to collate functions that convert a sequence of
                numpy arrays into a torch tensor.
        generator (torch.Generator):
            A torch generator for random number generation.
    """

    def __init__(
        self,
        collate_fn_map: dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]],
        generator: Optional[torch.Generator] = None,
    ) -> None:
        """Initialize a sequence collator.

        Args:
        collate_fn_map (dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]]):
            A dictionary mapping feature names to collate functions that convert a sequence of numpy arrays
            into a torch tensor.
        generator (Optional[torch.Generator]):
            An optional torch generator for random number generation. If not provided,
                a new generator will be created.
        """
        self.collate_fn_map = collate_fn_map
        self.add_position = "position" in collate_fn_map
        if generator is None:
            seed = int(torch.empty((), dtype=torch.int64).random_().item())
            self.generator = torch.Generator()
            self.generator.manual_seed(seed)
        else:
            self.generator = generator

    def __call__(self, batch: Sequence[dict[str, np.ndarray]]) -> TensorDict:
        """Collate feature dictionaries into a batched tensor dictionary.

        Args:
            batch: Sequence of feature dictionaries to collate.

        Returns:
            A tensor dictionary containing the collated batch.
        """
        batch_size = len(batch)
        context_size = len(next(iter(batch[0].values())))
        # transpose the batch of feature dictionaries to a dictionary of feature batches
        if self.add_position:
            return_batch: dict[str, list[np.ndarray]] = {
                k: [d[k] for d in batch] for k in self.collate_fn_map if k != "position"
            }
            return_batch["position"] = [
                np.arange(context_size) for i in range(batch_size)
            ]
        else:
            return_batch = {k: [d[k] for d in batch] for k in self.collate_fn_map}
        # apply the collate functions to the feature batches and return it as a TensorDict
        return_batch_2: TensorDict = TensorDict(
            {k: self.collate_fn_map[k](return_batch[k]) for k in self.collate_fn_map}
        )
        return_batch_2.batch_size_ = (batch_size, context_size)
        return return_batch_2


class MaskedLangModelingSequenceCollate(BaseSequenceCollate):
    """A collate function for training a masked language model on sequential
    data.

    In an input sequence target_ratio of the tokens will be targets for
    prediction, mask_ratio of the target tokens will be masked,
    perturb_ratio of the masked target tokens will be permuted, and the
    rest of the target tokens will be left unchanged.
    """

    def __init__(
        self,
        collate_fn_map: dict[str, Callable[[Sequence[np.ndarray]], torch.Tensor]],
        target_ratio: float = 0.15,
        mask_ratio: float = 0.8,
        perturb_ratio: float = 0.1,
        generator: Optional[torch.Generator] = None,
    ) -> None:
        """Initialize a masked language-model collator.

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
        """
        super().__init__(collate_fn_map, generator)
        self.target_ratio = target_ratio
        self.mask_ratio = mask_ratio
        self.perturb_ratio = perturb_ratio

    def __call__(self, batch: Sequence[dict[str, np.ndarray]]) -> TensorDict:
        """Collate a batch and apply masked-language-model preprocessing.

        Args:
            batch: Sequence of feature dictionaries to collate.

        Returns:
            A tensor dictionary containing masked and perturbed features.
        """
        return_batch: TensorDict = super().__call__(batch)
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
