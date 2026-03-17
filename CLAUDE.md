# CLAUDE.md

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
- **`CoreConfig`** / **`CoreParserConfig`** / **`CoreDetectorConfig`** — Pydantic-based configuration hierarchy

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

- **Parsers** (`src/detectmatelibrary/parsers/`): `JsonParser`, `DummyParser`, `TemplateMatcherParser` (uses Drain3 for template mining)
- **Detectors** (`src/detectmatelibrary/detectors/`): `NewValueDetector`, `NewValueComboDetector`, `RandomDetector`, `DummyDetector`
- **Utilities** (`src/detectmatelibrary/utils/`): `DataBuffer`, `EventPersistency`, `KeyExtractor`, `TimeFormatHandler`, `IdGenerator`

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

## Code Quality

Pre-commit hooks enforce:
- **mypy** strict mode
- **flake8** linting, **autopep8** formatting (max line 110)
- **bandit** security checks, **vulture** dead-code detection (70% threshold)
- **docformatter** docstring style

Python 3.12 is required (see `.python-version`).
