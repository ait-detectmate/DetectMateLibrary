"""Dependency rules between the packages of detectmatelibrary.

Persistency is a library behind one boundary, ``subcommon.TrackerDetector``.
These tests parse every module with ``ast`` (whole tree, so imports inside
functions count) and check:

R1  ``detectmatelibrary.utils.persistency`` is imported only from
    ``utils/persistency/`` and ``subcommon/``.
R2  ``common/`` imports neither ``subcommon`` nor ``detectors``.
R3  ``subcommon/`` does not import ``detectors``.
R4  ``utils/persistency/`` imports none of ``common``, ``subcommon``, ``detectors``.
"""
import ast
from pathlib import Path

import detectmatelibrary

PKG = "detectmatelibrary"
SRC = Path(detectmatelibrary.__file__).parent

PERSISTENCY = f"{PKG}.utils.persistency"
COMMON = f"{PKG}.common"
SUBCOMMON = f"{PKG}.subcommon"
DETECTORS = f"{PKG}.detectors"

# (rule, applies to module at this path, forbidden import prefixes)
RULES = [
    ("R1", lambda rel: not rel.startswith(("utils/persistency/", "subcommon/")), (PERSISTENCY,)),
    ("R2", lambda rel: rel.startswith("common/"), (SUBCOMMON, DETECTORS)),
    ("R3", lambda rel: rel.startswith("subcommon/"), (DETECTORS,)),
    ("R4", lambda rel: rel.startswith("utils/persistency/"), (COMMON, SUBCOMMON, DETECTORS)),
]

# Intentional: a stability tracker rebuilds the detector named in its saved
# state through importlib, to reuse that detector's add_value.
KNOWN_EXCEPTIONS = {
    ("R4", "utils/persistency/data_structures/trackers/stability/stability_tracker.py", DETECTORS),
}

# Violations the TrackerDetector refactor has not removed yet. Each task
# deletes the entries it fixes; the list is empty when the refactor is done.
_PENDING: set[tuple[str, str, str]] = set()


def _module_name(rel: str) -> str:
    parts = rel[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([PKG, *parts])


def _imported_names(tree: ast.AST, rel: str) -> set[str]:
    """Every module or module attribute ``tree`` imports, as absolute dotted
    names, including string literals passed to ``import_module``."""
    module = _module_name(rel)
    package = module if rel.endswith("__init__.py") else module.rpartition(".")[0]
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                parts = parts[: len(parts) - (node.level - 1)] + ([node.module] if node.module else [])
                base = ".".join(parts)
            else:
                base = node.module or ""
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            arg = node.args[0] if node.args else None
            if called == "import_module" and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                names.add(arg.value)
    return names


def find_violations(root: Path) -> set[tuple[str, str, str]]:
    """(rule, path relative to ``root``, forbidden prefix) for every rule a
    module under ``root`` breaks."""
    found = set()
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        names = _imported_names(ast.parse(path.read_text(), filename=str(path)), rel)
        for rule, applies, forbidden in RULES:
            if not applies(rel):
                continue
            for prefix in forbidden:
                if any(n == prefix or n.startswith(prefix + ".") for n in names):
                    found.add((rule, rel, prefix))
    return found


def test_no_new_violations() -> None:
    assert find_violations(SRC) - KNOWN_EXCEPTIONS - _PENDING == set()


def test_exceptions_and_pending_entries_are_still_real() -> None:
    # A stale entry would let the violation it names come back unnoticed.
    assert (KNOWN_EXCEPTIONS | _PENDING) - find_violations(SRC) == set()


def test_checker_reports_planted_violations(tmp_path: Path) -> None:
    (tmp_path / "common").mkdir()
    (tmp_path / "common" / "bad.py").write_text(
        "from detectmatelibrary.subcommon import TrackerDetector\n"
        "def lazy():\n"
        "    from ..utils.persistency import EventPersistency\n"
    )
    (tmp_path / "subcommon").mkdir()
    (tmp_path / "subcommon" / "ok.py").write_text(
        "from detectmatelibrary.utils.persistency import EventPersistency\n"
    )
    (tmp_path / "utils" / "persistency").mkdir(parents=True)
    (tmp_path / "utils" / "persistency" / "bad.py").write_text(
        "import importlib\n"
        "importlib.import_module('detectmatelibrary.common.detector')\n"
    )
    assert find_violations(tmp_path) == {
        ("R1", "common/bad.py", PERSISTENCY),
        ("R2", "common/bad.py", SUBCOMMON),
        ("R4", "utils/persistency/bad.py", COMMON),
    }
