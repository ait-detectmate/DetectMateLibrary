# Development

This section describes how to setup a development environment and how to contribute to `DetectMateLibrary`.

!!! note

    Read the [Contribution Guide](contribution.md) to follow and understand the development workflow.


## Setup a development environment

For development we recommend using [uv](https://docs.astral.sh/uv/). You can install all optional dependencies:

```bash
uv sync --dev
```

*Please note that this step is not necessary. `uv run --dev` will automatically download all dependencies.*


## Use prek to run code checks

Every code contributer must use [`prek`](https://github.com/j178/prek) to run basic checks at commit time.
`prek` is configured via the existing `.pre-commit-config.yaml`
and can be installed as part of the `dev` extras. To ensure pre-commit hooks run before each commit, run:

```bash
uv run prek install
```

To run the checks manually, you can execute:

```bash
uv run prek run -a
```

## Add tests and run pytest

In order to run the tests run the following command. The `dev` group already includes the `full` extra, so all optional dependencies are installed automatically:

```bash
uv run --dev pytest
```

## Implement auto-configuration in a detector

The user-facing side of auto-configuration is described in the [Detectors overview](detectors.md#auto-configuration-optional). This section covers what a detector has to implement to support it.

A detector that supports auto-configuration subclasses `base_detectors.TrackerDetector`, which builds two stores: `self.persistency` for training and detection, and a separate `self.auto_conf_persistency` for auto-configuration. Detectors never build stores from `utils.persistency` themselves:

```python
from detectmatelibrary.base_detectors import TrackerDetector, TrackerDetectorConfig


class MyDetectorConfig(TrackerDetectorConfig):
    method_type: str = "my_detector"


class MyDetector(TrackerDetector):
    def __init__(self, name="MyDetector", config=MyDetectorConfig()):
        super().__init__(name=name, config=config)
```

The `configure()` method ingests all available variables (not just configured ones) so the tracker can assess each one:

```python
def configure(self, input_):
    self.auto_conf_persistency.ingest_event(
        event_id=input_["EventID"],
        event_template=input_["template"],
        variables=input_["variables"],
        named_variables=input_["logFormatVariables"],
    )
```

The `set_configuration()` method queries the tracker results and writes the
final `events` block. It touches nothing else on the config  --  everything the
operator set under `params` or `auto_config_params` must survive untouched, so
`set_configuration` never rebuilds the config from scratch:

```python
def set_configuration(self):
    variables = {}
    for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
        stable_vars = tracker.get_features_by_classification("STABLE")
        variables[event_id] = stable_vars

    self.config.events = generate_events_config(variables, self.name)
    self.config.auto_config = False
```

### Why `auto_config_params` lives on `BasicConfig`

Both `auto_config` and `Component.configure()` are declared on the shared base,
so `auto_config_params` is declared there too  --  on `BasicConfig`, beside
`auto_config`  --  rather than on the detector config alone. Detectors are the only
component type with a real configure phase today, so they are the only ones that
narrow the block with fields; parsers and alert aggregators inherit it empty, and
an empty block is omitted from the serialized config, so their YAML is unaffected.
A component type that grows a configure phase later subclasses `AutoConfigParams`
and overrides the field, exactly as the variable, combo and sequence detector
families do.


## Write testable code snippets for the documentation

Code examples in the docs are not pasted inline. They live as standalone Python
files under `docs/examples/`, mirrored by category (`docs/examples/parsers/`,
`docs/examples/detectors/`), and are pulled into the Markdown pages via
[`pymdownx.snippets`](https://facelessuser.github.io/pymdown-extensions/extensions/snippets/).
This way every snippet in the docs is an actual `.py` file that gets executed by
the test suite in CI, so a broken example fails CI instead of silently shipping.

**1. Add the snippet file.** Put your example under `docs/examples/<category>/`.
By convention the filename matches its documentation page (`charset.md` →
`docs/examples/detectors/charset.py`). Wrap the part you want to show in section
markers:

```python
# ;--8<-- [start:basic]
from detectmatelibrary.parsers.logbatcher import LogBatcherParser, LogBatcherParserConfig
# ...
# ;--8<-- [end:basic]
```

**2. Include it in the `.md` page.** Paths are relative to the repo root
(`base_path` is set to `.`). Reference the section by name:

````markdown
```python
;--8<-- "docs/examples/parsers/logbatcher_parser.py:basic"
```
````

You can also include the whole file by dropping the `:section` suffix
(`--8<-- "docs/examples/parsers/template_tree_matcher.py"`), but section markers
are the norm. Because `check_paths: true` is set, the build aborts if the file or
marker doesn't exist  --  a missing snippet is caught at build time.

**3. Make sure it's testable.** The test (`tests/test_docs/test_doc_examples.py`)
globs every `.py` under `docs/examples/` and runs each one as a script via
`runpy.run_path(..., run_name="__main__")`. There is no plugin and no assert
requirement: a snippet passes as long as it runs standalone without raising. If
your example needs something unavailable in CI (e.g. an API key), comment out
those calls rather than letting them fail. The test is marked `ignored`, so a
plain `pytest` run skips it; pass `--run-ignored` (as CI does) to include it:

```bash
uv run --dev pytest --run-ignored                    # whole suite, snippets included
uv run --dev pytest tests/test_docs --run-ignored    # snippets only
```

**4. Component pages: a YAML file, and generated argument tables.** Each parser and
detector page shows a configuration file next to its example
(`docs/examples/<category>/<name>.yaml`). Keep it minimal: set only what the use
case needs, since every other parameter has a working default. The Python example
loads it with `yaml.safe_load`, so the snippet test also checks that the file is a
valid configuration. The "Configuration arguments" tables are generated from the
config classes. After adding or changing a config field, regenerate them from the
repo root:

```bash
uv run python docs/examples/config/update.py
```


## Render and verify the documentation

Build the static site:

```bash
uv run --dev mkdocs build
```

For a live local preview while editing:

```bash
uv run --dev mkdocs serve
```

`mkdocs` comes in via `mkdocs-material` (a direct dependency of the `dev` group),
so `--dev` is required. There is no `--strict` mode configured; the hard check on the docs is
`check_paths: true` from `pymdownx.snippets`, which fails the build on a missing
snippet or marker.
