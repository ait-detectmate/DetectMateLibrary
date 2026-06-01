"""Verification handlers for docs example blocks.

Each handler verifies one fenced block. ``dispatch`` applies the marker policy
(skip / expect-error) and routes by language. Python blocks execute in a shared
per-file namespace; YAML config blocks are validated through the library's real
``from_dict``.
"""
from __future__ import annotations

import functools
import importlib
import json
import pkgutil
import re
import warnings

import yaml

from tests.docs_examples.extractor import Example


@functools.lru_cache(maxsize=1)
def config_registry() -> dict[tuple[str, str], type]:
    """Build a ``(component_type, method_type) -> config class`` map by
    importing every ``detectmatelibrary`` submodule and walking ``BasicConfig``
    subclasses."""
    import detectmatelibrary

    for mod in pkgutil.walk_packages(
        detectmatelibrary.__path__, detectmatelibrary.__name__ + "."
    ):
        try:
            importlib.import_module(mod.name)
        except Exception:
            # Optional/heavy submodules that fail to import are simply skipped;
            # any config class they define won't be validated, which is acceptable.
            pass

    from detectmatelibrary.common._config import BasicConfig

    def _subclasses(cls: type):
        for sub in cls.__subclasses__():
            yield sub
            yield from _subclasses(sub)

    registry: dict[tuple[str, str], type] = {}
    for cls in set(_subclasses(BasicConfig)):
        try:
            inst = cls()
            registry.setdefault((inst.component_type, inst.method_type), cls)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"docs harness: could not instantiate config class {cls.__name__!r}; "
                f"YAML using its method_type will not be schema-validated ({exc})",
                stacklevel=2,
            )
    return registry


def _run_by_language(example: Example, namespace: dict) -> str:
    lang = example.language
    if lang == "python":
        return run_python(example, namespace)
    if lang == "yaml":
        return run_yaml(example)
    if lang == "bash":
        return run_bash(example)
    if lang == "json":
        return run_json(example)
    return "skipped"  # text/toml/markdown/empty: nothing to execute


def dispatch(example: Example, namespace: dict) -> str:
    """Apply marker policy and route the block.

    Returns one of:
    "ran", "skipped", "expected-error". Raises on verification failure.
    """
    marker = example.marker
    if marker is not None and marker.kind == "skip":
        return "skipped"

    if marker is not None and marker.kind == "expect-error":
        try:
            _run_by_language(example, namespace)
        except Exception as exc:  # noqa: BLE001 - we are asserting failure
            if marker.substring and marker.substring not in str(exc):
                raise AssertionError(
                    f"expected error containing {marker.substring!r}, got: {exc}"
                ) from exc
            return "expected-error"
        raise AssertionError("expected the example to raise, but it succeeded")

    return _run_by_language(example, namespace)


def run_python(example: Example, namespace: dict) -> str:
    code = compile(example.code, f"<{example.source_file}:{example.start_line}>", "exec")
    exec(code, namespace)  # noqa: S102
    return "ran"


def run_json(example: Example) -> str:
    json.loads(example.code)
    return "ran"


_COMPONENT_TYPES = ("parsers", "detectors")


def run_yaml(example: Example) -> str:
    data = yaml.safe_load(example.code)
    if not isinstance(data, dict):
        return "ran"  # valid YAML scalar/list, nothing to validate

    registry = config_registry()
    for component_type in _COMPONENT_TYPES:
        section = data.get(component_type)
        if not isinstance(section, dict):
            continue
        for method_id, block in section.items():
            if not isinstance(block, dict):
                continue
            method_type = block.get("method_type")
            config_cls = registry.get((component_type, method_type))
            if config_cls is None:
                continue  # unknown method_type: leave as "valid YAML only"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                config_cls.from_dict(data, method_id)
    return "ran"


_HEREDOC_RE = re.compile(
    r"cat\s*>\s*(?P<name>\S+)\s*<<\s*'?(?P<tag>\w+)'?\s*\n(?P<body>.*?)\n(?P=tag)",
    re.DOTALL,
)


def run_bash(example: Example) -> str:
    if example.marker is not None and example.marker.kind == "run":
        import subprocess  # noqa: PLC0415
        import tempfile  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as cwd:
            subprocess.run(  # noqa: S603
                ["bash", "-c", example.code], cwd=cwd, check=True,
                capture_output=True, text=True,
            )
        return "ran"

    validated = False
    for match in _HEREDOC_RE.finditer(example.code):
        name = match.group("name")
        if not (name.endswith(".yaml") or name.endswith(".yml")):
            continue
        synthetic = Example(
            source_file=example.source_file,
            start_line=example.start_line,
            language="yaml",
            code=match.group("body") + "\n",
            marker=None,
        )
        run_yaml(synthetic)
        validated = True

    return "ran" if validated else "skipped"
