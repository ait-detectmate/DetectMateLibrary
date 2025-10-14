from typing import Iterable, Type, Callable
from collections import defaultdict
from weakref import WeakSet
import importlib
import pkgutil

# A registry of tagged class sets
_CONFIG_REGISTRY: dict[str, WeakSet[type]] = defaultdict(WeakSet)
_DISCOVERED_MODULES: set[str] = set()

# --- Decorator(s) for classes ---


def detector_config(_cls: Type):
    """Decorator to mark a class as a configuration class."""
    fq_name = f"{_cls.__module__}.{_cls.__name__}"
    _CONFIG_REGISTRY[fq_name].add(_cls)
    return _cls

# --- Discovery functions ---


def find_config_classes_in_package(package: str | Iterable[str]) -> list[Type]:
    """Find all classes marked with @config decorator within the specified
    package(s).

    Imports the package modules and returns all registered config
    classes from those packages.
    """
    # Discover the package to ensure all modules are imported and decorators run
    _discover(package)
    # error if config registry is empty
    if not _CONFIG_REGISTRY:
        raise RuntimeError(f"No config classes found in {package}.")
    # Get all registered classes and filter by package
    all_classes = set()
    for class_set in _CONFIG_REGISTRY.values():
        all_classes.update(class_set)

    # Normalize packages for filtering
    packages = _normalize_packages(package)

    # Filter classes by package
    config_classes = []
    for cls in all_classes:
        if any(cls.__module__.startswith(pkg) for pkg in packages):
            config_classes.append(cls)

    # Nice, stable ordering: fully-qualified name
    return sorted(config_classes, key=lambda c: f"{c.__module__}.{c.__name__}")

# --- Internal helpers ---


def _discover(packages: str | Iterable[str]) -> None:
    """Import all modules in the given package(s) so decorators run.

    Call this once at startup if you rely on auto-discovery.
    """
    _walk_packages_with_filter(_normalize_packages(packages))


def _normalize_packages(packages: str | Iterable[str]) -> list[str]:
    """Helper to normalize package input to a list."""
    return [packages] if isinstance(packages, str) else list(packages)


def _import_module_safe(module_name: str) -> bool:
    """Safely import a module, returning True if successful."""
    if module_name in _DISCOVERED_MODULES:
        return True
    try:
        importlib.import_module(module_name)
        _DISCOVERED_MODULES.add(module_name)
        return True
    except ImportError:
        return False


def _walk_packages_with_filter(packages: list[str], filter_func: Callable[[str], bool] | None = None) -> None:
    """Walk through packages and import modules, optionally with a filter
    function.

    filter_func should return True to continue importing the module.
    """
    for pkg_name in packages:
        try:
            pkg = importlib.import_module(pkg_name)
            if not hasattr(pkg, "__path__"):
                # Single module, no subpackages
                _import_module_safe(pkg_name)
                continue

            for _finder, modname, _is_pkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
                if filter_func is None or filter_func(modname):
                    _import_module_safe(modname)

        except ImportError:
            continue
