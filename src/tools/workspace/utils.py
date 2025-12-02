import textwrap
import re
from pathlib import Path


def create_readme(name: str, ws_type: str, target_impl: Path, target_dir: Path) -> None:
    """Create a README.md file for the generated workspace.

    Parameters:
        name (str): Name of the workspace.
        ws_type (str): Type of workspace (parser/detector).
        target_impl (Path): Path to the main implementation file.
        target_dir (Path): Directory where the README will be created.
    """

    readme_text = textwrap.dedent(
        f"""
        # {name}

        This is a generated **{ws_type}** workspace created with:

        ```bash
        mate create --type {ws_type} --name {name} --dir {target_dir.parent}
        ```

        ## Contents

        - `{target_impl.name}`: starting point for your `{ws_type}` implementation.
        - `LICENSE.md`: copied from the main project.
        - `.pre-commit-config.yaml`: pre-commit hook configuration from the main project.
        - `.gitignore`: standard ignore rules from the main project.
        - `pyproject.toml`: Python project metadata and dependencies for this workspace.
        - `__init__.py`: makes this directory importable as a package.

        ## Next steps

        1. Open `{target_impl.name}` and implement your custom {ws_type}.
        2. (Optional) Install pre-commit hooks:

           ```bash
           pre-commit install
           ```

        3. Add the libraries your workspace needs to `pyproject.toml` under `dependencies`.
        4. Integrate this workspace with the rest of your project.
        """
    ).strip() + "\n"

    (target_dir / "README.md").write_text(readme_text)


def create_pyproject(name: str, ws_type: str, target_dir: Path) -> None:
    """Create a minimal pyproject.toml file for the generated workspace.

    - Uses the --name argument (normalized) as the project name.
    - Leaves a dependencies list ready for you to fill with the necessary libraries.
    """

    # Normalize name for project name (PEP 621 style)
    project_name = re.sub(r"[-_.]+", "-", name).lower()

    pyproject_text = textwrap.dedent(
        f"""
        [project]
        name = "{project_name}"
        version = "0.1.0"
        description = "Generated {ws_type} workspace '{name}'"
        readme = "README.md"
        requires-python = ">=3.12"

        # Add the libraries your workspace needs below
        dependencies = [
        ]

        [build-system]
        requires = ["setuptools>=64", "wheel"]
        build-backend = "setuptools.build_meta"

        [tool.setuptools]
        # Treat the '{name}' directory as the package
        packages = ["{name}"]
        """
    ).strip() + "\n"

    (target_dir / "pyproject.toml").write_text(pyproject_text)
