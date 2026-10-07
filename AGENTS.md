# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DetectMateLibrary is a Python library for log processing and anomaly detection. It provides composable, stream-friendly components (parsers and detectors) that communicate via Protobuf-based schemas. The library is designed for both single-process and microservice deployments.

## Development Commands

```bash
# Install dependencies and pre-commit hooks
uv sync --dev
uv run prek install

# Run tests
uv run pytest -q
uv run pytest -s                                      # verbose with stdout
uv run pytest --cov=. --cov-report=term-missing       # with coverage
uv run pytest tests/test_foo.py                       # single test file

# Run linting/formatting (all pre-commit hooks)
uv run prek run -a

# Recompile Protobuf (only if schemas.proto is modified)
protoc --proto_path=src/detectmatelibrary/schemas/ \
  --python_out=src/detectmatelibrary/schemas/ \
  src/detectmatelibrary/schemas/schemas.proto

# Scaffold a new component workspace
mate create --type <parser|detector> --name <name> --dir <target_dir>
```

## Architecture

### Data Flow

```
Raw Logs → Parser → ParserSchema → Detector → DetectorSchema (Alerts)
```

All data flows through typed Protobuf-backed schema objects. Components are stateful and support an optional training phase before detection.

### Core Abstractions (`src/detectmatelibrary/common/`)

- **`CoreComponent`** — base class managing buffering, ID generation, and training state
  - **`CoreParser(CoreComponent)`** — parse raw logs into `ParserSchema`
  - **`CoreDetector(CoreComponent)`** — detect anomalies in `ParserSchema`, emit `DetectorSchema`
- **`CoreConfig`** / **`CoreParserConfig`** / **`CoreDetectorConfig`** — Pydantic-based configuration hierarchy (`extra="forbid"`)

#### Component Lifecycle (FitLogic)

Each `process()` call passes through a state machine controlled by config fields:

| Config field | Meaning |
|---|---|
| `data_use_configure` | How many items to run through `configure()` before training. `None` = skip. |
| `data_use_training` | How many items to run through `train()` before detection. `None` = skip. |

Phases in order: **CONFIGURE → TRAIN → DETECT** (phases are skipped when the corresponding field is `None`).

State control enums allow overriding automatic transitions: `TrainState.KEEP_TRAINING` / `STOP_TRAINING` and `EnumState.KEEP` / `STOP_CONFIGURE` on the component's `fit_logic`.

#### CoreDetectorConfig: EventsConfig

Detectors use a nested `events` structure to select which variables to track per event ID, plus `global_instances` for event-ID-independent variables (e.g., hostname, level):

```yaml
detectors:
  MyDetector:
    method_type: new_value_detector
    auto_config: false          # true = auto-discover variables from training data
    persist:                    # tracker detectors only — omit to disable state saving
      path: ./state             # base path; detector name is appended automatically
      interval_seconds: 300     # save every N seconds
      events_until_save: null   # also save after N ingested events (null = disabled)
      auto_load: false          # restore saved state on construction
      storage_options: {}       # fsspec credentials (S3, Azure, GCS, etc.)
    events:
      login_failure:            # named event ID (string) or integer EventID
        instance_label:         # arbitrary instance name
          params: {}
          variables:
            - pos: pid          # named wildcard label OR integer position in ParserSchema.variables[]
              name: pid
          header_variables:
            - pos: Type         # key in ParserSchema.logFormatVariables{}
              params: {}
    global:                     # event-ID-independent instances (GLOBAL_EVENT_ID = "*")
      global_monitor:
        header_variables:
          - pos: Level
            params: {}
```

Named event IDs (strings) and named variable positions require templates loaded from a CSV with an `EventId` column. Call `TemplateMatcher.compile_detector_config(config)` to resolve names to integers at setup time.

Use `generate_detector_config()` (`src/detectmatelibrary/common/_config/_compile.py`) to build this programmatically:

```python
from detectmatelibrary.common._config import generate_detector_config

config = generate_detector_config(
    variable_selection={1: ["var_0", "var_1"]},
    detector_name="MyDetector",
    method_type="new_value_detector",
)
```

Load/save configs via `BasicConfig.from_dict(d, method_id=...)` and `.to_dict(method_id=...)` for YAML round-trip compatibility.

After training completes, variable detectors with `auto_config=False` automatically call `validate_config_coverage()` (`src/detectmatelibrary/subcommon/_tracker_persist.py`, from `VariableDetector.post_train`), which logs warnings when configured EventIDs or variable positions were never observed in training data. This catches config/data mismatches early — check logs after the training phase when adding new detector configs.

### Detector families (`src/detectmatelibrary/subcommon/`)

A layer between `common/` and `detectors/`, imported as `from detectmatelibrary.subcommon import ...`:

- **`TrackerDetector(CoreDetector)`** — the only owner of persistency. Builds the `EventPersistency` stores (`persistency`, `auto_conf_persistency`), starts the `persist:` saver, implements `export_state`/`import_state` and federation (`to_binary`, `from_binary`, `aggregate_strategy`, `finalize_federation`). `TrackerDetectorConfig` adds `persist` and `allow_fed`.
  - **`VariableDetector(TrackerDetector)`** — per-variable model detectors (NewValue, Combo, Charset, ValueRange, BigramFrequency).
  - NewEvent, EventSequence, SCVS and ECVC subclass `TrackerDetector` directly.
- **`DeepLearningDetector(CoreDetector)`** — DeepLog and LogBERT. Rule and Random subclass `CoreDetector`.

`CoreComponent.export_state()` returns `None` and `import_state()` is a no-op; only `TrackerDetector` has state. A `persist:` block on a non-tracker detector is a validation error.

`tests/test_architecture.py` enforces the dependency rules: `utils.persistency` is imported only from `utils/persistency/` and `subcommon/`; `common/` imports neither `subcommon` nor `detectors`; `subcommon/` does not import `detectors`; `utils/persistency/` imports none of the three.

### Schema System (`src/detectmatelibrary/schemas/`)

- `BaseSchema` wraps generated Protobuf messages with dict-like access (`schema["field"]`)
- Key schemas: `LogSchema`, `ParserSchema`, `DetectorSchema`
- Support serialization to/from bytes for transport and persistence

### Buffering Modes (`src/detectmatelibrary/utils/data_buffer.py`)

Three modes via `ArgsBuffer` config:
- **NO_BUF** — one item at a time (default)
- **BATCH** — accumulate N items, process as batch
- **WINDOW** — sliding window of size N

### Implementations

- **Parsers** (`src/detectmatelibrary/parsers/`): `JsonParser`, `LogBatcherParser`, `DummyParser`, `MatcherParser` (Drain3 template mining; supports named wildcards `<username>` alongside positional `<*>`)
- **Detectors** (`src/detectmatelibrary/detectors/`): `NewValueDetector`, `NewValueComboDetector`, `RandomDetector`, `DummyDetector`
- **Utilities** (`src/detectmatelibrary/utils/`): `DataBuffer`, `EventPersistency` (used only through `subcommon.TrackerDetector`), `KeyExtractor`, `TimeFormatHandler`, `IdGenerator`
- Uses the `regex` package (not stdlib `re`) — relevant when writing type annotations or imports involving patterns

## Extending the Library

Implement a custom detector by subclassing `CoreDetector`:

```python
class MyDetectorConfig(CoreDetectorConfig):
    method_type: str = "my_detector"
    my_param: int = 10

class MyDetector(CoreDetector):
    def __init__(self, name="MyDetector", config=MyDetectorConfig()):
        super().__init__(name=name, config=config)

    def train(self, input_: ParserSchema) -> None:
        pass  # optional

    def detect(self, input_: ParserSchema, output_: DetectorSchema) -> bool:
        output_["detectorID"] = self.name
        output_["score"] = 0.0
        return False  # True = anomaly detected
```

Same pattern applies for `CoreParser` — implement `parse(input_: LogSchema, output_: ParserSchema) -> bool`.

### Wiring persist support into a new detector

A detector that keeps state in `EventPersistency` stores subclasses `TrackerDetector`; it never imports `utils.persistency` or builds stores itself. `TrackerDetector` then provides the stores, the `persist:` block, `export_state`/`import_state` and federation.

**1. Subclass `TrackerDetector` and its config:**

```python
from detectmatelibrary.subcommon import TrackerDetector, TrackerDetectorConfig

class MyDetectorConfig(TrackerDetectorConfig):
    method_type: str = "my_detector"

class MyDetector(TrackerDetector):
    def __init__(self, name="MyDetector", config=MyDetectorConfig()):
        super().__init__(name=name, config=config)

    def train(self, input_: ParserSchema) -> None:
        self._ingest(input_, variables={...}, event_id=input_["EventID"])
```

Pass tracker kwargs by overriding `_event_data_kwargs()` / `_auto_conf_kwargs()`; build an extra store with `self._new_store()`.

**2. Rebuild derived fields in `_sync_from_state()`, and mind the ordering rule:**

Anything computed from the stores (a count vector, a window length) goes in a `_sync_from_state()` override. `TrackerDetector` calls it at the end of `__init__` (after a possible `auto_load`), after `import_state()`, on the detector `from_binary()` returns, and on every component after `aggregate_strategy()`. The first call runs inside `TrackerDetector.__init__`, so everything the override reads or writes must exist before `super().__init__()` returns — declare it as a class attribute (ECVC's `count_vecs`) or assign it before the `super().__init__()` call (EventSequence's windows).

**3. Write only your outputs in `set_configuration()` — never rebuild `self.config`:**

`set_configuration()` must not reassign `self.config` (e.g. via `from_dict()`). Write only what the configure phase produced, then flip `auto_config` off:

```python
def set_configuration(self) -> None:
    variables = {...}  # whatever the configure phase decided
    self.config.events = generate_events_config(variables, self.name)
    self.config.auto_config = False
```

(`EventSequenceDetector` additionally writes `self.config.fixed_window_size`, since its configure phase picks a window length rather than a variable selection.)

Every other field — `persist`, `auto_config_params`, any detector-specific param — is operator input and is left untouched by construction, since nothing here reassigns `self.config`. Rebuilding the config wholesale is what used to drop `persist` (and everything else) silently.

## Code Quality

Pre-commit hooks enforce:
- **mypy** strict mode
- **flake8** linting, **autopep8** formatting (max line 110)
- **bandit** security checks, **vulture** dead-code detection (70% threshold)
- **docformatter** docstring style

Python 3.12 is required (see `.python-version`).


# Git
NEVER include "Co-Authored-By ..." in your commit or PR messages.

Design documents (files under `docs/design/`) must NEVER be committed to the repository.
