# DetectMateLibrary

Main library to run the different components in DetectMate.

## Main structure

The library contains the next components:

* **Readers**: insert logs into the system.
* **Parsers**: parse the logs receive from the reader.
* **Detectors**: return alerts if anomalies are detected.
* **Outputs**: return alerts as outputs.
* **Schemas**: standard data classes use in DetectMate.
```
+---------+     +--------+     +-----------+     +--------+
| Reader  | --> | Parser | --> |  Detector | --> | Output |
+---------+     +--------+     +-----------+     +--------+
```
## Developer setup:

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

## Workspace generator (`mate create`)

DetectMateLibrary includes a small CLI helper to bootstrap standalone workspaces
for custom parsers and detectors. This is useful if you want to develop and test
components in isolation while still using the same library and schemas.

### Usage

The CLI entry point is `mate` with a `create` command:

```bash
mate create --type <parser|detector> --name <workspace_name> --dir <target_dir>
```

| Option   | Description                                                                                                                                                                   |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--type` | Component type to generate:<br>- `parser`: CoreParser-based template<br>- `detector`: CoreDetector-based template                                                             |
| `--name` | Name of the component and package:<br>- Creates package dir: `<target_dir>/<name>/`<br>- Creates main file: `<name>.py`<br>- Derives class names: `<Name>` and `<Name>Config` |
| `--dir`  | Directory where the workspace will be created                                                                                                                                 |


### What gets generated

For example:

```bash
mate create --type parser --name custom_parser --dir ./workspaces/custom_parser
```

will create:

```text
workspaces/custom_parser/          # workspace root
├── custom_parser/                 # Python package
│   ├── __init__.py
│   └── custom_parser.py           # CoreParser-based template
├── tests/
│   └── test_custom_parser.py      # generated from template to test custom_parser
├── LICENSE.md                     # copied from main project
├── .gitignore                     # copied from main project
├── .pre-commit-config.yaml        # copied from main project
├── pyproject.toml                 # minimal project + dev extras
└── README.md                      # setup instructions
```
