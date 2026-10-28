from typing import Any, Collection, List
from typing_extensions import Self, override
import warnings

from detectmatelibrary.base_detectors import (
    SequenceAutoConfigParams,
    TrackerDetector,
    TrackerDetectorConfig,
    choose_window_length,
    feed_candidate_windows,
    warn_if_never_configured,
)
from detectmatelibrary.common._config._compile import generate_events_config
from detectmatelibrary.common.detector import _extract_logIDs, _extract_timestamp

from detectmatelibrary.tools.logging import logger
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.sequence_encoding import (
    build_count_vec,
    decode_count_vec,
    encode_count_vec,
)
from detectmatelibrary import schemas

from collections import Counter, deque
from math import ceil
import numpy as np
from pydantic import Field


class ECVCOp:
    build_count_vec = staticmethod(build_count_vec)

    @staticmethod
    def build_one_vec(input_: List[schemas.ParserSchema], n: int) -> np.ndarray:
        events = [in_["eventID"] for in_ in input_]
        arr = np.zeros(n if n > (m := max(events) + 1) else m)

        for e in events:
            arr[e] += 1

        return arr

    @staticmethod
    def init_count_matrix(seqs: Collection[tuple[int, ...]]) -> np.ndarray:
        m, n = len(seqs), max([len(s) for s in seqs])
        matrix = np.zeros((m, n))

        for i, seq in enumerate(seqs):
            for j, c in enumerate(seq):
                matrix[i, j] = c

        return matrix

    @staticmethod
    def calculate_score(y: np.ndarray, matrix: np.ndarray) -> float:
        pad = np.zeros((matrix.shape[0], y.shape[0] - matrix.shape[1]))
        matrix_ = np.concat([matrix, pad], axis=1)

        score = np.inf
        for m in matrix_:
            dif = np.sum(np.abs(m - y))
            div = np.sum(np.max(np.concat([m[np.newaxis], y[np.newaxis]]).T, axis=1))
            score = score if score < (s := (dif / div)) else s

        return float(score)

    @staticmethod
    def threshold_cal(y_s: np.ndarray, matrix: np.ndarray, method: str) -> float:
        if method == "mean":
            return float(np.mean([ECVCOp.calculate_score(y, matrix=matrix) for y in y_s]))
        elif method == "default":
            return 0.0

        raise Exception("Method not supported")


# method_type this detector used before it was corrected; still accepted.
_LEGACY_METHOD_TYPE = "ecvc_detector_detector"
# Name of fixed_window_size before auto-configuration existed; still accepted.
_LEGACY_WINDOW_KEY = "window_size"
_WINDOW_KEY = "fixed_window_size"


def _rename_legacy_window_size(method: dict[str, Any]) -> dict[str, Any]:
    """Return `method` with a legacy `window_size` renamed to
    `fixed_window_size`.

    Looks in the method entry and in its `params` block, and renames on a
    copy, so the caller's dict is left untouched. Returns `method` itself
    when neither holds the legacy key. Raises ValueError when
    `fixed_window_size` is given as well, rather than letting one silently
    win.
    """
    params = method.get("params")
    blocks = [method, params] if isinstance(params, dict) else [method]
    if not any(_LEGACY_WINDOW_KEY in block for block in blocks):
        return method
    if any(_WINDOW_KEY in block for block in blocks):
        raise ValueError(
            f"Both '{_LEGACY_WINDOW_KEY}' and '{_WINDOW_KEY}' are set. '{_LEGACY_WINDOW_KEY}' "
            f"is a deprecated alias of '{_WINDOW_KEY}'; keep only '{_WINDOW_KEY}'."
        )

    def rename(block: dict[str, Any]) -> dict[str, Any]:
        return {(_WINDOW_KEY if key == _LEGACY_WINDOW_KEY else key): value for key, value in block.items()}

    renamed = rename(method)
    if isinstance(params, dict):
        renamed["params"] = rename(params)
    return renamed


class ECVCDetectorConfig(TrackerDetectorConfig):
    method_type: str = Field(
        default="ecvc_detector", description="Indicates what type of method it is."
    )
    fixed_window_size: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Length of the window of consecutive logs a count vector is built "
            "over. When set it overrides the `auto_config_params` window range "
            "and skips auto-configuration; auto-configuration writes its own "
            "choice here. While it is None the detector is unconfigured and "
            "neither trains nor alerts."
        ),
    )
    validation_per: float = Field(
        default=0.2,
        description=(
            "Fraction of the learned count vectors held out as a validation "
            "split and used to derive the anomaly threshold."
        ),
    )
    seed: int = Field(
        default=0,
        description="Random seed used to shuffle count vectors into train/validation splits.",
    )
    threshold_method: str = Field(
        default="mean",
        description=(
            "Method used to derive the anomaly threshold from the validation "
            "split: 'mean' averages the distance scores, 'default' uses a "
            "fixed threshold of 0."
        ),
    )

    auto_config_params: SequenceAutoConfigParams = SequenceAutoConfigParams()

    @classmethod
    def from_dict(cls, data: dict[str, Any], method_id: str) -> Self:
        component_type = cls().component_type
        method = data.get(component_type, {}).get(method_id, {})
        updated = _rename_legacy_window_size(method)  # raises on a conflict, before any warning
        if updated is not method:
            warnings.warn(
                f"'{_LEGACY_WINDOW_KEY}' is deprecated, use '{_WINDOW_KEY}'.",
                DeprecationWarning,
                stacklevel=2,
            )
        if method.get("method_type") == _LEGACY_METHOD_TYPE:
            warnings.warn(
                f"method_type '{_LEGACY_METHOD_TYPE}' is deprecated, use 'ecvc_detector'.",
                DeprecationWarning,
                stacklevel=2,
            )
            updated = {**updated, "method_type": "ecvc_detector"}
        if updated is not method:
            data = {**data, component_type: {**data[component_type], method_id: updated}}
        return super().from_dict(data, method_id)


class ECVCDetector(TrackerDetector):
    """Detect windows whose EventID counts are far from every count vector
    learned in training."""

    # Class-level defaults: _sync_from_state runs inside TrackerDetector.__init__.
    count_vecs: np.ndarray | None = None
    threshold: float = 0.0

    def __init__(
        self,
        name: str = "ECVCDetector",
        config: ECVCDetectorConfig | dict[str, Any] | None = None,
    ) -> None:
        # A fresh default per instance: restored state and auto-configuration change the config.
        if config is None:
            config = ECVCDetectorConfig()
        elif isinstance(config, dict):
            config = ECVCDetectorConfig.from_dict(config, name)
        self.config: ECVCDetectorConfig

        # Built before super().__init__(), whose _sync_from_state resizes them.
        self._train_window: deque[schemas.ParserSchema] = deque(maxlen=config.fixed_window_size)
        self._detect_window: deque[schemas.ParserSchema] = deque(maxlen=config.fixed_window_size)
        self._configure_windows: dict[int, deque[schemas.ParserSchema]] = {}
        self._restored_length: int | None = None
        self._warned_unconfigured = False
        self._warned_empty_split = False

        super().__init__(
            name=name,
            config=config,
            buffer_mode=BufferMode.NO_BUF,
            stability_params=config.auto_config_params,
        )

        if not self.config.auto_config and self.config.fixed_window_size is None:
            logger.warning(
                f"[{self.name}] auto_config=False but no fixed_window_size was given. "
                "The detector stays unconfigured and will neither train nor alert."
            )
        # count_vecs come from post_train(), which needs a training phase, or from restored state.
        if self.config.data_use_configure and not self.config.data_use_training and self.count_vecs is None:
            logger.warning(
                f"[{self.name}] data_use_configure is set but data_use_training is not set, so no "
                "training phase runs. No count vectors are learned from training; the detector will "
                "not alert unless learned state is restored (auto_load, import_state, federation)."
            )

    def _set_window_length(self, length: int) -> None:
        """Set the window size and resize both sliding windows to match."""
        self.config.fixed_window_size = length
        self._train_window = deque(self._train_window, maxlen=length)
        self._detect_window = deque(self._detect_window, maxlen=length)

    def _match_window_length(self, length: int) -> None:
        """Resize both windows when `fixed_window_size` changed under them.

        The config object can be shared: by detectors built from one
        instance, or by the component from_binary() restores into. When
        one of them picks or adopts a size it writes it into the shared
        config, while the others' windows keep their old length.
        """
        if self._train_window.maxlen != length or self._detect_window.maxlen != length:
            self._set_window_length(length)

    def _adopt_restored_length(self) -> None:
        """Align `fixed_window_size` with restored state, if any.

        A count vector is only comparable within the window it was
        counted over, so a model trained at one size cannot be evaluated
        at another: every window would miss and alert. The persisted size
        therefore wins over the configured one. State that mixes sizes
        (e.g. merged from nodes that chose different sizes) has no valid
        size and raises.
        """
        restored = self.persistency.get_events_seen()
        if not restored:
            self._restored_length = None
            return

        sizes = dict(sorted(Counter(decode_count_vec(str(key))[0] for key in restored).items()))
        if len(sizes) > 1:
            raise ValueError(
                f"[{self.name}] restored state mixes count vectors of window sizes {sizes} "
                "(window size: number of count vectors). Count vectors of different window "
                "sizes are not comparable; restore state trained at a single window size."
            )
        (length,) = sizes
        if length != self.config.fixed_window_size:
            logger.warning(
                f"[{self.name}] restored state holds count vectors of window size {length}, but "
                f"fixed_window_size is {self.config.fixed_window_size}. Using the persisted size "
                "— the restored model is only valid at that size."
            )
            self._set_window_length(length)
        else:
            # The config may already hold the persisted size while these windows do not:
            # from_binary() restores into a component that shares this detector's config,
            # and that component adopted the size (and warned) first. Resize silently.
            self._match_window_length(length)
        self._restored_length = length

    @override
    def _sync_from_state(self) -> None:
        self._adopt_restored_length()
        self.build_count_vec()  # no-op while no count vectors are stored

    def train(self, input_: schemas.ParserSchema) -> None:  # type: ignore
        """Learn the count vector of the window ending at this log.

        No-op while the window size is unconfigured.
        """
        if (length := self.config.fixed_window_size) is None:
            self._warned_unconfigured = warn_if_never_configured(
                self.name, self.config, self._warned_unconfigured
            )
            return
        self._match_window_length(length)
        self._train_window.append(input_)
        if len(self._train_window) < length:
            return
        self._ingest(
            event_id=encode_count_vec(length, ECVCOp.build_count_vec(list(self._train_window))),
            input_=input_,
            variables={},
        )

    def build_count_vec(self) -> None:
        seqs = sorted(
            decode_count_vec(str(encoded))[1]
            for encoded in self.persistency.get_events_seen()
        )
        if not seqs:
            return

        train_idx = ceil(len(seqs) * (1 - self.config.validation_per))
        np.random.seed(self.config.seed)
        matrix = ECVCOp.init_count_matrix(seqs)[np.random.permutation(len(seqs))]

        self.count_vecs, val = matrix[:train_idx], matrix[train_idx:]
        if len(val) > 0:
            self.threshold = ECVCOp.threshold_cal(
                y_s=val, matrix=self.count_vecs, method=self.config.threshold_method
            )
        elif not self._warned_empty_split:
            self._warned_empty_split = True
            logger.warning(
                f"[{self.name}] validation split is empty: {len(seqs)} distinct count vector(s) at "
                f"validation_per={self.config.validation_per}. Keeping the threshold at "
                f"{self.threshold}: a window alerts when its distance to the closest learned "
                "count vector exceeds it."
            )

    def post_train(self) -> None:
        self.build_count_vec()
        # Not in build_count_vec(): it also runs on every sync, and in __init__ with empty state.
        # No size means auto-configuration found none, which choose_window_length already reported.
        if (length := self.config.fixed_window_size) is not None and self.count_vecs is None:
            logger.warning(
                f"[{self.name}] training ended before a window of {length} logs filled; no count "
                "vectors were learned and the detector will not alert unless learned state is "
                "restored."
            )

    def detect(
        self, input_: schemas.ParserSchema, output_: schemas.DetectorSchema,  # type: ignore
    ) -> bool:
        """Score the window ending at this log against the learned count
        vectors.

        The window fills even before anything is learned, so it is warm
        when training ends. An alert lists every log of the window. Does
        nothing while the window size is unconfigured.
        """
        if (length := self.config.fixed_window_size) is None:
            self._warned_unconfigured = warn_if_never_configured(
                self.name, self.config, self._warned_unconfigured
            )
            return False
        self._match_window_length(length)
        self._detect_window.append(input_)
        if len(self._detect_window) < length or self.count_vecs is None:
            return False

        window = list(self._detect_window)
        score = ECVCOp.calculate_score(ECVCOp.build_one_vec(
            window, self.count_vecs.shape[1]), matrix=self.count_vecs
        )
        if score > self.threshold:
            output_["score"] = score
            output_["description"] = "ECVC found an anominal sequence"
            output_["logIDs"] = _extract_logIDs(window)
            output_["logTimestamps"] = _extract_timestamp(window)
            return True

        return False

    def configure(self, input_: schemas.ParserSchema) -> None:  # type: ignore
        """Feed the log into one sliding window per candidate size.

        Nothing to decide once `fixed_window_size` is set, whether by the
        user or by restored state.
        """
        if self.config.fixed_window_size is not None:
            return
        auto = self.config.auto_config_params
        for length, window in feed_candidate_windows(self._configure_windows, input_, auto):
            self.auto_conf_persistency.ingest_event(
                event_id=length,
                event_template=input_["template"],
                named_variables={"cvec": ECVCOp.build_count_vec(list(window))},
                timestamp=self._timestamps.read(input_),
            )

    def set_configuration(self) -> None:
        """Choose `fixed_window_size` from the configure-phase data.

        Each candidate size is scored by the stability of the count
        vectors it produced; the longest STABLE or STATIC candidate
        wins. Candidates whose window never filled during the configure
        phase, or filled too few times to classify, are skipped. When
        nothing is stable an empty configuration is generated — this
        detector then holds no instance and stays silent, which beats
        alerting on every window at an arbitrary size.
        """
        if (fixed := self.config.fixed_window_size) is not None:
            reason = (
                "persisted state was restored"
                if self._restored_length is not None
                else "fixed_window_size is set"
            )
            logger.warning(
                f"[{self.name}] auto_config=True but {reason}. Keeping window size "
                f"{fixed}."
            )
            self._release_configure_state()
            return

        chosen = choose_window_length(
            self.name,
            self.auto_conf_persistency.get_events_data(),
            "cvec",
            self.config.auto_config_params,
        )
        self.config.events = generate_events_config({}, self.name)
        if chosen is not None:
            self._set_window_length(chosen)
        self.config.auto_config = False
        self._release_configure_state()

    def _release_configure_state(self) -> None:
        """Drop configure-phase state, which nothing reads afterwards."""
        self._configure_windows.clear()
        self.auto_conf_persistency = self._new_store()
