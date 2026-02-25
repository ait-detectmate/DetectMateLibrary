# Getting started: Installation

This document explains how to set up and run DetectMateLibrary for users and developers.

## User setup

**Purpose**: install the library so you can import and use DetectMate in your projects.

**Recommended**: use the provided `uv` helper (bundled Python environment manager used in this repo). If you prefer pip/venv, create a virtualenv first.

Install the package in editable mode:

```bash
uv sync
```

**Result**: the package is installed into the active Python environment and changes to the source tree are reflected immediately.

## Developer setup

**Purpose**: prepare a development environment with test and lint tooling.

### Step 1: Install Python development dependencies & pre-commit hooks

- Install dev dependencies (testing, linters, formatters):

```bash
uv sync --dev
```

- Install pre-commit hooks (this repository uses `prek` to run pre-commit tooling):

```bash
uv run --dev prek install
```

**Notes**:

- Ensure `uv` is available in PATH. If not, use your system Python + virtualenv and then `uv sync --dev`.
- Run the pre-commit hooks locally with `uv run --dev prek run -a` before committing to catch style/typing issues early.

### Step 2: Install Protobuf toolchain (only if you change proto files)

**Purpose**: compile .proto definitions into Python code.

Install protoc on Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y protobuf-compiler
protoc --version
```

Compile the project proto:

```bash
protoc \
  --proto_path=src/detectmatelibrary/schemas/ \
  --python_out=src/detectmatelibrary/schemas/ \
  src/detectmatelibrary/schemas/schemas.proto
```

**Result**: generated Python modules appear under `src/detectmatelibrary/schemas/`. If you edit proto files, re-run this command and commit generated code if required by your workflow.

### Step 3: Run unit tests

Run the full test suite:

```bash
uv run --dev pytest -s
```

Run tests with coverage (terminal summary):

```bash
uv run --dev pytest --cov=. --cov-report=term-missing
```

**Tips**:

- Run a single test or directory to speed iteration: `uv run --dev pytest tests/some_test.py::test_name -q`

## Troubleshooting

- If `uv` is unavailable, use a Python virtualenv and the `pip`/`pytest` commands directly.
- If `protoc` is missing, install the system package or download a prebuilt binary for your OS.
- Always run commands from the project root so file paths (pyproject.toml, src/) resolve correctly.

Go back to [Index](index.md) or proceed to [Basic usage](basic_usage.md).
