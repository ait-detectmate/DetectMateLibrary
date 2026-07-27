
import detectmatelibrary.utils.deep_learning._op as op
import detectmatelibrary.utils.deep_learning.deeplog as deeplog
import detectmatelibrary.utils.deep_learning.logbert as logbert

import jax.numpy as jnp
import jax


class TestDLOp:
    def test_checkpoint(self) -> None:
        checkpoint = op.CheckPoint(patience=2)

        assert not checkpoint(0.1, 1, {"hi": "is not mee"})
        assert not checkpoint(0.02, 2, {"hi": "is mee"})
        assert not checkpoint(0.2, 2, {"hi": "is not mee"})
        assert checkpoint(0.2, 2, {"hi": "is not mee"})

        epoch, param = checkpoint.load_checkpoint()
        assert epoch == 2
        assert {"hi": "is mee"} == param

    def test_mask(self) -> None:
        mask = op.Mask(seq_size=4, mask_per=0.5)

        mask_tensor_1 = mask(3)

        assert mask_tensor_1.shape == (3, 4)
        for i in range(3):
            assert mask_tensor_1[i].sum() == 2

        mask_tensor_2 = mask(3)

        assert not jnp.array_equal(mask_tensor_1, mask_tensor_2)
        for i in range(3):
            assert mask_tensor_2[i].sum() == 2


class TestDeeplog:
    def test_deeplog_model(self) -> None:
        model = deeplog.DeepLogModel(hidden_dim=4, n_layers=1, output_size=1)

        x = jnp.ones((3, 4, 1), dtype=jnp.float32)
        params = model.init(jax.random.PRNGKey(0), x[:1])['params']

        y = model.apply({"params": params}, x)
        assert y.shape == (3, 1)

    def test_deeplog_train(self) -> None:
        config = {
            "Model": {
                "hidden_dim": 4,
                "n_layers": 1,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
            },
        }
        deeplog_ = deeplog.DeepLog(config=config)
        stats = deeplog_.train(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert not deeplog_.check_anomaly((1, 2, 0, 1), stats["top_k"])
        assert deeplog_.check_anomaly((1, 2, 2, 0), stats["top_k"])

    def test_deeplog_finetune(self) -> None:
        config = {
            "Model": {
                "hidden_dim": 8,
                "n_layers": 1,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
            },
            "finetune": [
                ("Model", "hidden_dim", [4, 5])
            ]
        }
        deeplog_ = deeplog.DeepLog(config=config)
        deeplog_.finetune(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert deeplog_.config != config


class TestLogBert:
    def test_logbert_model(self) -> None:
        model = logbert.LogBertModel(
            n_embed=3, hidden=8, num_heads=1, n_layers=1, dropout=0.0, max_len=10
        )

        params = model.init(jax.random.PRNGKey(0), jnp.zeros((1, 5), dtype=jnp.int32))['params']
        x = jnp.ones((3, 10), dtype=jnp.int32)

        y, dist = model.apply({"params": params}, x)
        assert y.shape == (3, 10, 3)
        assert dist.shape == (3, 8)

    def test_logbert_train(self) -> None:
        config = {
            "Model": {
                "hidden": 4,
                "n_layers": 1,
                "num_heads": 4,
                "dropout": 0.0,
                "max_len": 10,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
            },
        }
        logbert_ = logbert.LogBert(config=config)
        stats = logbert_.train(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert not logbert_.check_anomaly((1, 2, 0, 1), stats["top_k"])
        assert logbert_.check_anomaly((1, 2, 3, 0), stats["top_k"])

    def test_logbert_finetune(self) -> None:
        config = {
            "Model": {
                "hidden": 4,
                "n_layers": 1,
                "num_heads": 1,
                "dropout": 0.0,
                "max_len": 10,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
            },
            "finetune": [
                ("Model", "n_layers", [2, 3])
            ]
        }
        logbert_ = logbert.LogBert(config=config)
        logbert_.finetune(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert logbert_.config != config
