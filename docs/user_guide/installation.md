# Installation

It is recommended to use [uv](https://docs.astral.sh/uv/) for installation. From
the project root:

```bash
uv sync
```

(If you prefer pip/venv, create a virtualenv first.)

Changes to the source tree are then reflected immediately. To install DetectMate
as a library into a different environment instead:

```bash
uv pip install --no-cache-dir <directory_detectmatelibrary>
```

## Optional dependencies

Not every feature needs the same dependencies, so DetectMate uses optional
extras --> you install only what you need.

| Extra | Installs | When you need it |
|---|---|---|
| `llm` | `openai`, `tenacity`, `scipy`, `scikit-learn`, `tiktoken`, `pandas` | Using the `LogBatcherParser` (LLM-based log parsing) |
| `dataframes` | `pandas`, `polars` | Using `EventDataFrame`, `ChunkedEventDataFrame`, or `DataNormalizer` |
| `polars-rtcompat` | `polars[rtcompat]` | Running on older CPUs without AVX2 support (e.g. some VMs or embedded hardware); not needed for standard deployments |
| `full` | `llm` + `dataframes` + `polars-rtcompat` | Installing every optional extra at once |

Install an extra with `uv sync`:

```bash
uv sync --extra dataframes
```

Or with `uv pip install` / `pip` when installing as a library:

```bash
uv pip install "detectmatelibrary[dataframes]"
# or
pip install "detectmatelibrary[dataframes]"
```

Combine multiple extras if needed:

```bash
uv sync --extra dataframes --extra polars-rtcompat
```

Or install everything at once with the `full` extra:

```bash
uv sync --extra full
# or
uv pip install "detectmatelibrary[full]"
```

## Developer setup

### Step 1: Install Python development dependencies & pre-commit hooks

* Install dev dependencies (testing, linters, formatters). The `dev` group also pulls in the `full` extra, so every optional dependency (LLM, dataframes, polars-rtcompat) is installed too:

```bash
uv sync --dev
```

* Install pre-commit hooks (this repository uses `prek` to run pre-commit tooling):

```bash
uv run --dev prek install
```

**Notes:**

* Ensure `uv` is available in PATH. If not, use your system Python + virtualenv and then `uv sync --dev`.
* Run the pre-commit hooks locally with `uv run --dev prek run -a` before committing to catch style/typing issues early.

### Step 2: Install Protobuf toolchain (only if you change proto files)

**Purpose:** compile `.proto` definitions into Python code.

* Install `protoc` on Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y protobuf-compiler
protoc --version
```

* Compile the project proto:

```bash
protoc \
  --proto_path=src/detectmatelibrary/schemas/ \
  --python_out=src/detectmatelibrary/schemas/ \
  src/detectmatelibrary/schemas/schemas.proto
```

**Result:** generated Python modules appear under `src/detectmatelibrary/schemas/`. If you edit proto files, re-run this command and commit generated code if required by your workflow.

### Step 3: Run unit tests

The full test suite covers dataframe and LLM-parser code, so all extras must be present. Since `uv sync --dev` already installs the `full` extra, run all tests with:

```bash
uv run --dev pytest -s
```

* Run tests with coverage (terminal summary):

````bash
uv run --dev pytest --cov=. --cov-report=term-missing
````

**Tips:**

* Run a single test or directory to speed iteration: `uv run --dev pytest tests/some_test.py::test_name -q`

### Troubleshooting

* If `uv` is unavailable, use a Python virtualenv and the `pip`/`pytest` commands directly.
* If `protoc` is missing, install the system package or download a prebuilt binary for your OS.
* Always run commands from the project root so file paths (`pyproject.toml`, `src/`) resolve correctly.

Go back [Index](../index.md)
