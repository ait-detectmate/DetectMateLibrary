# Installation

## Requirements

- **Python 3.12 or newer.** If you don't have it, uv can install it for you:
  `uv python install 3.12`.
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip.
- **git**, to get the source code.

## Install from source

It is recommended to use [uv](https://docs.astral.sh/uv/) for installation. Clone
the repository and install it from the project root:

```console title="Install from source"
git clone https://github.com/ait-detectmate/DetectMateLibrary.git
cd DetectMateLibrary
uv sync
```

(If you prefer pip/venv, create a virtualenv first.)

Changes to the source tree are then reflected immediately. To install DetectMate
as a library into a different environment instead:

```console title="Install with pip"
uv pip install --no-cache-dir /path/to/DetectMateLibrary
```

## Optional dependencies

Not every feature needs the same dependencies, so DetectMate uses optional
extras: you install only what you need.

| Extra | Installs | When you need it |
|---|---|---|
| `llm` | `openai`, `tenacity`, `scipy`, `scikit-learn`, `tiktoken`, `pandas` | Using the `LogBatcherParser` (LLM-based log parsing). |
| `alertbert` | `torch`, `tensordict`, `scikit-learn`, `scipy` | Using the `AlertBERTAggregation`. |
| `full` | All of the above. | Installing every optional extra at once. |

To have a closer look at all the dependencies, see [Optional dependencies](https://pydevtools.com/handbook/explanation/what-are-optional-dependencies-and-dependency-groups/).

Install an extra with `uv sync`:

```console  title="Install optional dependencies"
uv sync --extra llm
```

Or with `uv pip install` / `pip` when installing as a library:

```console title="Install optional dependencies with pip"
uv pip install "detectmatelibrary[llm]"
```

Combine multiple extras if needed:

```console title="Install multiple optional dependencies"
uv sync --extra llm --extra alertbert
```

Or install everything at once with the `full` extra:

```console title="Install all dependencies"
uv pip install "detectmatelibrary[full]"
```

## Developer setup

!!! warning "Only needed for development"
    Only follow these steps if you are contributing to DetectMate.

### Step 1: Install Python development dependencies & pre-commit hooks

Install the development dependencies for testing, linting, and formatting. The `dev` group includes the `full` extra, which installs all optional dependencies.

```console title="Install development dependencies"
uv sync --dev
```

Install the pre-commit hooks with `prek`.

```console title="Install pre-commit hooks"
uv run --dev prek install
```

**Notes:**

* Ensure `uv` is on your `PATH` before running these commands.
* Run the pre-commit hooks locally with `uv run --dev prek run -a` before committing to catch style/typing issues early.

### Step 2: Install Protobuf toolchain (only if you change proto files)

**Purpose:** compile `.proto` definitions into Python code.

* Install `protoc` on Debian/Ubuntu:

```console title="Install Protobuf on Linux"
sudo apt-get update
sudo apt-get install -y protobuf-compiler
protoc --version
```

* Compile the project proto:

```console title="Compile the Protobuf schema"
protoc \
  --proto_path=src/detectmatelibrary/schemas/protobuf/ \
  --python_out=src/detectmatelibrary/schemas/protobuf/ \
  src/detectmatelibrary/schemas/protobuf/schemas.proto
```

**Result:** generated Python modules appear under `src/detectmatelibrary/schemas/protobuf/`. If you edit proto files, re-run this command and commit generated code if required by your workflow.

### Step 3: Run unit tests

The full test suite covers dataframe and LLM-parser code, so all extras must be present. Since `uv sync --dev` already installs the `full` extra, run the fast tests with:

```console  title="Run unit tests"
uv run --dev pytest -s
```

Add `--run-deeplearning` to include the deep-learning utility tests in this run.
The full test run below includes them through `--run-ignored`.
[Run just the deep-learning utility tests](../development.md#add-tests-and-run-pytest)

To run all unit tests, first start the database containers:

```console title="Start the databases"
docker compose -f tests/test_schemas/compose.yaml up -d
```

and then run:

```console title="Run all the unit tests"
uv run pytest --run-ignored --run-ignored-mongo --run-ignored-redis
```


* Run tests with coverage (terminal summary):

````console title="Run unit tests with coverage"
uv run --dev pytest --cov=. --cov-report=term-missing
````

**Tips:**

* Run a single test or directory to speed iteration: `uv run --dev pytest tests/some_test.py::test_name -q`

### Troubleshooting

* If `uv` is unavailable, use a Python virtualenv and the `pip`/`pytest` commands directly.
* If `protoc` is missing, install the system package or download a prebuilt binary for your OS.
* Always run commands from the project root so file paths (`pyproject.toml`, `src/`) resolve correctly.
