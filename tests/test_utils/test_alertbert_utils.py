from pathlib import Path

import numpy as np
import pytest
import torch
from tensordict import TensorDict
from torch import nn

from detectmatelibrary.schemas import DetectorSchema
from detectmatelibrary.utils.alertbert.datasets import (
    AlertDataset,
    AlertSequenceBatchSampler,
    AlertSequenceSampler,
    MergeAlertSequences,
    detectorschema_to_dict,
    split_alert_dataset,
)
from detectmatelibrary.utils.alertbert.models import (
    AbstractDatasetGroupingModel,
    EncoderLayer,
    EncoderMLP,
    MaskedLangModelEmbeddingLayer,
    MaskedLangModelEncoder,
    MaskedLangModelEvalWrapper,
    MaskedLangModelInferenceWrapper,
    MaskedLangModelTrainWrapper,
    MultiClassificationHead,
    MultiTargetLoss,
    RotaryEmbedding,
    SelfAttention,
    TimeDelta,
)
from detectmatelibrary.utils.alertbert.preprocessing import (
    BaseSequenceCollate,
    MaskedLangModelingSequenceCollate,
    Vocabulary,
    default_collate_fn,
)


def make_alert(
    alert_id: str, timestamp: int, description: str = "login"
) -> DetectorSchema:
    return DetectorSchema(
        {
            "detectorID": "detector",
            "detectorType": "dummy",
            "alertID": alert_id,
            "detectedTimestamp": timestamp,
            "logIDs": [f"log-{alert_id}"],
            "score": 0.0,
            "logTimestamps": [timestamp],
            "description": description,
            "receivedTimestamp": timestamp,
            "alertDetails": {"severity": "low"},
        }
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


def test_alert_dataset_converts_alerts_and_supports_indexing() -> None:
    alerts = [make_alert(str(i), i, description=f"event-{i}") for i in range(3)]
    dataset = AlertDataset(alerts)

    assert len(dataset) == 3
    assert dataset[0]["relevantTimestamp"] == 0
    assert dataset[-1]["alertID"] == "2"
    assert dataset[1:]["alertID"] == ["1", "2"]
    assert dataset[np.array([2, 0])]["alertID"] == ["2", "0"]
    assert detectorschema_to_dict(alerts[0])["alertDetails:severity"] == "low"
    with pytest.raises(TypeError):
        dataset["invalid"]  # type: ignore[index]


def test_split_dataset_and_sequence_samplers() -> None:
    dataset = AlertDataset(make_alert(str(i), i) for i in range(10))
    train, validation, test = split_alert_dataset(
        dataset, (0.5, 0.3, 0.2), drop_first_n=2
    )

    assert len(train) == 4
    assert len(validation) == 2
    assert len(test) == 2
    assert train[0]["alertID"] == "2"
    with pytest.raises(ValueError):
        split_alert_dataset(dataset, (0.5, 0.5, 0.5))

    generator = torch.Generator().manual_seed(2)
    sampler = AlertSequenceSampler(
        dataset, context_size=3, cyclic=False, generator=generator, shuffle=False
    )
    slices = list(sampler)
    assert len(sampler) == 3
    assert all(s.stop - s.start == 3 for s in slices)
    batches = list(
        AlertSequenceBatchSampler(
            dataset, context_size=3, batch_size=2, drop_last=False
        )
    )
    assert len(batches) == 2
    cyclic = AlertSequenceSampler(
        dataset, context_size=4, cyclic=True, generator=generator, shuffle=False
    )
    assert len(list(cyclic)) == 3


def test_merge_alert_sequences_orders_sources_and_skips_empty_sources() -> None:
    sources = {
        "first": iter([make_alert("a", 1), make_alert("c", 3)]),
        "second": iter([make_alert("b", 2)]),
    }
    merged = MergeAlertSequences(sources)
    merged.add_source("empty", iter([]))

    assert [alert["alertID"] for alert in merged] == ["a", "b", "c"]
    merged.add_source("later", iter([make_alert("d", 4)]))
    assert [alert["alertID"] for alert in merged] == ["d"]


def test_alertbert_neural_components() -> None:
    vocabulary = Vocabulary()
    vocabulary.build_from_iterator(["a", "b"])
    embedding = MaskedLangModelEmbeddingLayer(
        ["token"], None, {"token": vocabulary}, dim=4, context_size=3
    )
    embedded = embedding(token=torch.tensor([[2, 3]]))
    assert embedded.shape == (1, 2, 4)

    rotary = RotaryEmbedding(4, [1.0])
    q = torch.ones((1, 1, 2, 4))
    rotated_q, rotated_k = rotary(q, q, torch.tensor([[0.0, 1.0]]))
    assert rotated_q.shape == q.shape
    assert torch.equal(rotated_q[:, :, :1], rotated_k[:, :, :1])
    with pytest.raises(ValueError):
        rotary._get_rotation(torch.ones((1, 2), dtype=torch.int64))

    attention = SelfAttention(4, 1)
    assert attention(torch.ones((1, 2, 4))).shape == (1, 2, 4)
    assert attention(torch.ones((1, 2, 4)), return_attn_weights=True).shape == (
        1,
        1,
        2,
        2,
    )
    assert EncoderMLP(4, 8, gated_activation=False)(torch.ones((1, 2, 4))).shape == (
        1,
        2,
        4,
    )
    layer = EncoderLayer(4, 1, 8)
    assert layer(torch.ones((1, 2, 4))).shape == (1, 2, 4)
    encoder = MaskedLangModelEncoder(4, 1, 2, 8)
    assert encoder(torch.ones((1, 2, 4))).shape == (1, 2, 4)

    head = MultiClassificationHead(4, ["token"], {"token": vocabulary})
    assert head(torch.ones((1, 2, 4)))[0].shape[-1] == vocabulary.num_targets
    loss = MultiTargetLoss([nn.CrossEntropyLoss(), nn.L1Loss()])
    result = loss(
        (torch.ones(2, 3), torch.ones(2)),
        (torch.zeros(2, dtype=torch.long), torch.zeros(2)),
    )
    assert result.ndim == 0


def test_time_delta_and_abstract_grouping_model() -> None:
    config = type("Config", (), {"delta": 10.0})()
    assert np.array_equal(
        TimeDelta(config).forward([make_alert("a", 1), make_alert("b", 12)]),
        [0, 1],
    )
    with pytest.raises(NotImplementedError):
        AbstractDatasetGroupingModel().forward([])


def test_alertbert_clustering_helpers_merge_labels() -> None:
    from detectmatelibrary.utils.alertbert.models import AlertBERT

    alertbert = object.__new__(AlertBERT)
    alertbert.config = type("Config", (), {"delta": 1.0})()
    components, count = alertbert._dist_matrix_to_connected_components(
        np.array([[0.0, 0.5, 2.0], [0.5, 0.0, 2.0], [2.0, 2.0, 0.0]]),
        3,
    )
    assert count == 2
    assert components[0] == components[1] != components[2]
    labels, count = alertbert._unite_labels(
        np.array([0, 0, 1, 2]), np.array([3, 4, 4, 5])
    )
    assert count == 2
    assert labels.tolist() == [0, 0, 0, 1]
    with pytest.raises(ValueError):
        alertbert._unite_labels(np.array([0]), np.array([0, 1]))
    with pytest.raises(ValueError):
        alertbert._unite_labels(np.array([0]), np.array([0]))


class TinyMaskedLanguageModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        vocabulary = Vocabulary()
        vocabulary.build_from_iterator(["a", "b"])
        self.vocabs = {"token": vocabulary}
        self.config = {"encoding": "position"}
        self.embedding = MaskedLangModelEmbeddingLayer(
            ["token"], "position", self.vocabs, dim=4, context_size=3
        )
        self.encoder = EncoderLayer(4, 1, 8)
        self.head = MultiClassificationHead(4, ["token"], self.vocabs)

    def __getitem__(self, key: str) -> nn.Module:
        return getattr(self, key)

    def forward(self, **src: torch.Tensor) -> tuple[torch.Tensor]:  # ty: ignore[invalid-mutable-override]
        embedded = self.embedding(**src)
        encoded = self.encoder(embedded, src[self.config["encoding"]])
        return self.head(encoded)


def make_model_batch() -> TensorDict:
    return MaskedLangModelingSequenceCollate(
        {"token": default_collate_fn, "position": default_collate_fn},
        target_ratio=1.0,
        mask_ratio=0.0,
        perturb_ratio=0.0,
        generator=torch.Generator().manual_seed(0),
    )([{"token": np.array([2, 3, 2]), "position": np.array([0, 1, 2])}])


def test_model_wrappers_compute_masked_outputs_and_loss() -> None:
    model = TinyMaskedLanguageModel()
    inference = MaskedLangModelInferenceWrapper(model, layers=("embedding", "encoder"))
    inference_result = inference(
        TensorDict(
            {
                "token": torch.tensor([[2, 3, 2]]),
                "position": torch.tensor([[0, 1, 2]]),
            },
            batch_size=[1, 3],
        )
    )
    assert inference_result["output"].shape == (1, 3, 4)

    evaluation = MaskedLangModelEvalWrapper(model)
    evaluated = evaluation(make_model_batch())
    assert evaluated["token_true"].shape == (3,)
    assert evaluated["token_pred_mask"].shape == (3, model.vocabs["token"].num_targets)

    training = MaskedLangModelTrainWrapper(
        model, MultiTargetLoss([nn.CrossEntropyLoss()])
    )
    trained = training(make_model_batch())
    assert trained["loss"].ndim == 0


def test_model_vocabulary_helpers_and_classification_report(tmp_path: Path) -> None:
    from detectmatelibrary.utils.alertbert.models import MaskedLanguageModel

    model = object.__new__(MaskedLanguageModel)
    model.path = str(tmp_path)
    dataset = AlertDataset(
        [make_alert("a", 1, "a"), make_alert("b", 2, "b"), make_alert("c", 3, "a")]
    )
    model._build_feature_vocabs(dataset, ["description"], min_freq=1)
    assert model.vocabs["description"].counter["a"] == 2
    model.vocabs["description"].save(str(tmp_path / "vocab_description.json"))
    model._load_feature_vocabs(["description"], min_freq=1)
    assert model.vocabs["description"]("a") == 2

    stats = {
        "loss": 0.5,
        "corr": 0.5,
        "true": torch.tensor([0, 1, 1, 0]),
        "pred": torch.tensor([0, 1, 0, 0]),
        "rank": torch.tensor([1, 2, 3, 1]),
    }
    report = model._classification_report(stats)
    assert report["top_2_accuracy"] == 0.75
    assert 0.0 <= report["macro_f1"] <= 1.0


def test_alertbert_embedding_and_time_cosine_metric() -> None:
    from detectmatelibrary.utils.alertbert.models import AlertBERT

    alertbert = object.__new__(AlertBERT)
    alertbert.dim_reduction = None
    alertbert.readout = 2048
    alertbert.padding = 1024
    alertbert.config = type("Config", (), {"theta": 4.0})()
    with pytest.raises(ValueError):
        alertbert._get_embeddings([], apply_dim_red=True)

    x = np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 12.0]])
    distances = alertbert.time_cosine_metric(x)
    cross_distances = alertbert.time_cosine_metric(x[0], x[1])
    assert distances.shape == (2, 2)
    assert cross_distances.shape == (1, 1)
    assert distances[0, 1] == 2.0
