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

## Write testable code snippets for the documentation

Code examples in the docs are not pasted inline. They live as standalone Python
files under `docs/examples/`, mirrored by category (`docs/examples/parsers/`,
`docs/examples/detectors/`), and are pulled into the Markdown pages via
[`pymdownx.snippets`](https://facelessuser.github.io/pymdown-extensions/extensions/snippets/).
This way every snippet in the docs is an actual `.py` file that gets executed by
the test suite, so a broken example fails CI instead of silently shipping.

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
marker doesn't exist — a missing snippet is caught at build time.

**3. Make sure it's testable.** The test (`tests/test_docs/test_doc_examples.py`)
globs every `.py` under `docs/examples/` and runs each one as a script via
`runpy.run_path(..., run_name="__main__")`. There is no plugin and no assert
requirement: a snippet passes as long as it runs standalone without raising. If
your example needs something unavailable in CI (e.g. an API key), comment out
those calls rather than letting them fail. Run the snippet tests together with
the rest of the suite:

```bash
uv run --dev pytest
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

`mkdocs` comes in transitively via `mike` in the `dev` group, so `--dev` is
required. There is no `--strict` mode configured; the hard check on the docs is
`check_paths: true` from `pymdownx.snippets`, which fails the build on a missing
snippet or marker.
