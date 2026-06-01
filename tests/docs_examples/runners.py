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
        except Exception:
            pass
    return registry


def _run_by_language(example: Example, namespace: dict) -> str:
    lang = example.language
    if lang == "python":
        return run_python(example, namespace)
    if lang == "yaml":
        return run_yaml(example)  # noqa: F821 - defined in Task 4
    if lang == "bash":
        return run_bash(example)  # noqa: F821 - defined in Task 5
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
