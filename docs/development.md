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

In oder to run the tests run the following command:

```bash
uv run --dev pytest
```
