"""Tests for detectmatelibrary.utils.alertbert.preprocessing."""
from pathlib import Path
import numpy as np
import torch
from detectmatelibrary.utils.alertbert.preprocessing import (
    BaseSequenceCollate,
    MaskedLangModelingSequenceCollate,
    Vocabulary,
    default_collate_fn,
)


def test_compute_targets_accepts_int64_tokens() -> None:
    vocabulary = Vocabulary()
    tokens = torch.tensor([1, 2], dtype=torch.int64)

    targets = vocabulary.compute_targets(tokens)

    assert targets.dtype == torch.int64
    assert torch.equal(targets, torch.tensor([0, 1], dtype=torch.int64))


def test_vocabulary_builds_maps_unknown_words_and_frequencies(tmp_path: Path) -> None:
    vocabulary = Vocabulary(min_freq=2)
    vocabulary.build_from_iterator(["a", "a", "b", "c"])

    assert vocabulary("a") == 2
    assert vocabulary("b") == 1
    assert vocabulary([["a", "unknown"]]).tolist() == [[2, 1]]
    assert torch.allclose(vocabulary.get_frequencies(), torch.tensor([0.5, 0.5]))

    path = tmp_path / "vocabulary.json"
    vocabulary.save(str(path))
    loaded = Vocabulary(min_freq=2)
    loaded.load(str(path))
    assert loaded.counter == vocabulary.counter
    assert list(loaded) == list(vocabulary)

    vocabulary.remove(["c"])
    assert "c" not in vocabulary.counter
    assert len(vocabulary) == 3


def test_collate_functions_stack_sequences_and_apply_masking() -> None:
    batch = [
        {"token": np.array([1, 2, 3]), "position": np.array([10, 11, 12])},
        {"token": np.array([4, 5, 6]), "position": np.array([20, 21, 22])},
    ]
    generator = torch.Generator().manual_seed(0)
    collate = BaseSequenceCollate(
        {"token": default_collate_fn, "position": default_collate_fn},
        generator=generator,
    )
    result = collate(batch)

    assert result.batch_size_ == torch.Size([2, 3])
    assert result["token"].tolist() == [[1, 2, 3], [4, 5, 6]]
    assert result["position"].tolist() == [[0, 1, 2], [0, 1, 2]]

    masked_batch = [
        {"token": item["token"], "raw_time": item["position"]} for item in batch
    ]
    masked = MaskedLangModelingSequenceCollate(
        {"token": default_collate_fn, "raw_time": default_collate_fn},
        target_ratio=1.0,
        mask_ratio=1.0,
        perturb_ratio=0.0,
        generator=torch.Generator().manual_seed(1),
    )(masked_batch)
    assert masked["mask"].all()
    assert masked["token_mask"].sum() == 0
    assert masked["mask_index"].shape == (2, 6)
