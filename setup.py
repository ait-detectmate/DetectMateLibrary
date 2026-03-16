from setuptools import setup, find_packages
import tomllib


def gather_dependencies(toml_path: str = "pyproject.toml") -> list[str]:
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    # Try Poetry first
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if poetry_deps:
        return [f"{dep}{version}" for dep, version in poetry_deps.items()]

    # Fall back to PEP 621
    project_deps: list[str] = data.get("project", {}).get("dependencies", [])
    return project_deps


setup(
    name="detectmatelibrary",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    description="DetectMate Library for log processing components",
    author="voice",
    author_email="voice@example.com",
    install_requires=gather_dependencies(),
)
