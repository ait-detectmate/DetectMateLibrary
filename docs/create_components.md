
# Getting started:  Create new component

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




Go back to [Index](index.md), to previous step: [Basic usage](basic_usage.md) or to next step: [Implement new component](implement_components.md).
