# Core Component Prototype

This project demonstrates a basic `CoreComponent` class designed to be inherited by other specialized components.


### Developer setup:

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
