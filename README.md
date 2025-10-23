# DetectMateLibrary

Main library to run the different components in DetectMate.

## Developer setup:

### Step 1:Install dependencies
Set up the dev environment and install pre-commit hooks:

```bash
uv pip install -e .[dev]
pre-commit install
```

Run the tests:

```bash
uv run pytest -q
```


#### Protobuf
Installation
```bash
sudo apt install -y protobuf-compiler
protoc --version
```
Compilation
```
protoc --proto_path=src/schemas/ --python_out=src/schemas/ src/schemas/schemas.proto
```
