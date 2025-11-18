# DetectMateLibrary

Main library to run the different components in DetectMate.

## Main structure

The library contains the next components:

* **Readers**: insert logs into the  system.
* **Parsers**: parse the logs receive from the reader.
* **Detectors**: return alerts if anomalies are detected.
* **Schemas**: standard data classes use in DetectMate.
```
+---------+     +--------+     +-----------+
| Reader  | --> | Parser | --> |  Detector |
+---------+     +--------+     +-----------+
```
## Developer setup:

### Step 1: Install python dependencies
Set up the dev environment and install pre-commit hooks:

```bash
uv pip install -e .[dev]
uv run prek install
```

### Step 2: Install Protobuf dependencies
To installed in linux do:
```bash
sudo apt install -y protobuf-compiler
protoc --version
```
This dependency is only need if a proto files is modifiy. To compile the proto file do:
```
protoc --proto_path=src/schemas/ --python_out=src/schemas/ src/schemas/schemas.proto
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
