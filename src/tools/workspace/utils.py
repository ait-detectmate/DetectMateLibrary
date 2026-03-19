import textwrap
import re
from pathlib import Path


def normalize(name: str) -> str:
    """Normalize name for project name (PEP 621 style)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize_package_name(name: str) -> str:
    """Normalize to a valid Python package name: lowercase, underscores only."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)  # replace non-alphanumerics w/ _
    name = re.sub(r"_+", "_", name)  # collapse repeated _
    name = name.strip("_")
    return name


def create_readme(name: str, ws_type: str, target_impl: Path, target_dir: Path) -> None:
    """Create a README.md file for the generated workspace.

    Parameters:
        name (str): Name of the workspace.
        ws_type (str): Type of workspace (parser/detector).
        target_impl (Path): Path to the main implementation file.
        target_dir (Path): Directory where the README will be created.
    """
    # Import path to the implementation module, e.g. "MyCoolThing.MyCoolThing"

    readme_text = textwrap.dedent(
        f"""
        # {name}

        This is an auto-generated workspace for implementing your custom {ws_type}.
        The directory containing this `README.md` is referred to as the *workspace root* below.

        ## Contents

        - `{normalize(name)}/{target_impl.name}`: starting point for your `{ws_type}` implementation.
        - `tests/test_{target_impl.name}`: unit tests for your `{ws_type}`.
        - `LICENSE.md`: EUPL-1.2 license copied from the main project.
        - `.pre-commit-config.yaml`: recommended pre-commit hook configuration.
        - `.gitignore`: standard ignore rules.
        - `pyproject.toml`: Python project metadata, dependencies, and dev extras.

        ## Recommended setup (uv + prek)

        We recommend using [`uv`](https://github.com/astral-sh/uv) to manage the environment
        and dependencies, and [`prek`](https://github.com/j178/prek) to manage Git
        pre-commit hooks. `prek` is configured via the existing `.pre-commit-config.yaml`
        and can be installed as part of the `dev` extras.

        ### 1. Create and activate a virtual environment with uv

        From the workspace root (the directory containing this `README.md`):

        ```bash
        cd <workspace-root>

        # Create a virtual environment (if you don't have one yet)
        uv venv

        # Activate it
        source .venv/bin/activate         # Linux/macOS
        # .venv\\Scripts\\activate          # Windows
        ```

        ### 2. Install the project and dev dependencies

        ```bash
        uv pip install -e .[dev]
        ```

        ### 3. Install and run Git hooks with prek (optional but recommended)

        With the virtual environment activated:

        ```bash
        # Install Git hooks from .pre-commit-config.yaml using prek
        uv sync

        # You can run all hooks on the full codebase with:
        # prek run --all-files
        ```

        After this, hooks will run automatically on each commit.


        ## Next steps

        Open `{target_impl.name}` and implement your custom {ws_type}. Execute it with example data doing:

        ```python
        python {target_impl.name.replace('.py', '')}/{target_impl.name}
        ```
        and run the custom unit tests doing:

        ```python
        python -m pytest
        ```

        For more information check the official documentation:

        * [DetectMateLibrary](https://ait-detectmate.github.io/DetectMateLibrary/latest/)
        * [DetectMateService](https://ait-detectmate.github.io/DetectMateService/latest/)
        """
    ).strip() + "\n"

    (target_dir / "README.md").write_text(readme_text)


def create_pyproject(name: str, ws_type: str, target_dir: Path) -> None:
    """Create a minimal pyproject.toml file for the generated workspace.

    - Uses the --name argument (normalized) as the project name.
    - Leaves a dependencies list ready for you to fill with the necessary libraries.
    """

    package_name = normalize_package_name(name)

    pyproject_text = textwrap.dedent(
        f"""
        [project]
        name = "{normalize(name)}"
        version = "0.1.0"
        description = "Generated {ws_type} workspace '{name}'"
        readme = "README.md"
        requires-python = ">=3.12"

        # Add the libraries your workspace needs below
        dependencies = [
            "detectmatelibrary @ git+https://github.com/ait-detectmate/DetectMateLibrary.git",
        ]

        [project.optional-dependencies]
        # Add dependencies in this section with: uv add --optional dev <package>
        # Install with all the dev dependencies:  uv pip install -e .[dev]
        dev = [
            "detectmateservice @ git+https://github.com/ait-detectmate/DetectMateService.git",
            "prek>=0.2.8",
            "pytest>=8.4.2",
        ]

        [build-system]
        requires = ["setuptools>=64", "wheel"]
        build-backend = "setuptools.build_meta"

        [tool.setuptools]
        # Treat the '{package_name}' directory as the package
        packages = ["{package_name}"]
        """
    ).strip() + "\n"

    (target_dir / "pyproject.toml").write_text(pyproject_text)
