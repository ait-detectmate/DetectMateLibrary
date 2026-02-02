# Getting started:  Installation

Setup all the dependencies of DetectMate Library.

## User setup:

Setup use for using DetectMate.

```bash
uv pip install -e .
```

## Developer setup:

Setup use for DetectMate development.

### Step 1: Install python dependencies
Set up the dev environment and install pre-commit hooks:

```bash
uv pip install -e .[dev]
uv run prek install
```

### Step 2: Install Protobuf dependencies

To install in Linux do:

```bash
sudo apt install -y protobuf-compiler
protoc --version
```

This dependency is only needed if a proto file is modified. To compile the proto file do:
```bash
protoc --proto_path=src/detectmatelibrary/schemas/ --python_out=src/detectmatelibrary/schemas/ src/detectmatelibrary/schemas/schemas.proto
```

### Step 3: Run unit tests
Run the tests:

```bash
uv run pytest -q
```

Run the tests with coverage (add --cov-report=html to generate an HTML report):

```bash
uv run pytest --cov=. --cov-report=term-missing
```

Go back to [Index](index.md) or to next step: [Basic usage](basic_usage.md).
