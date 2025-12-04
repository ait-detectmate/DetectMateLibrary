import textwrap
import re
from pathlib import Path


def normalize(name: str) -> str:
    """Normalize name for project name (PEP 621 style)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def create_readme(name: str, ws_type: str, target_impl: Path, target_dir: Path) -> None:
    """Create a README.md file for the generated workspace.

    Parameters:
        name (str): Name of the workspace.
        ws_type (str): Type of workspace (parser/detector).
        target_impl (Path): Path to the main implementation file.
        target_dir (Path): Directory where the README will be created.
    """
    # Import path to the implementation module, e.g. "MyCoolThing.MyCoolThing"
    impl_module = f"{target_dir.name}.{target_impl.stem}"

    readme_text = textwrap.dedent(
        f"""
        # {name}

        This is a generated **{ws_type}** workspace created with:

        ```bash
        mate create --type {ws_type} --name {name} --dir {target_dir.parent}
        ```

        The directory containing this `README.md` is referred to as the *workspace root* below.

        ## Contents

        - `{target_impl.name}`: starting point for your `{ws_type}` implementation.
        - `LICENSE.md`: copied from the main project.
        - `.pre-commit-config.yaml`: pre-commit hook configuration from the main project.
        - `.gitignore`: standard ignore rules from the main project.
        - `pyproject.toml`: Python project metadata, dependencies, and dev extras.
        - `__init__.py`: makes this directory importable as a package.

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
        # .venv\\Scripts\\activate        # Windows (PowerShell / CMD)
        ```

        ### 2. Install the project and dev dependencies (including prek)

        ```bash
        uv pip install -e .[dev]
        ```

        To add new dev-only dependencies later:

        ```bash
        uv add --optional dev <package>
        ```

        ### 3. Install and run Git hooks with prek

        With the virtual environment activated:

        ```bash
        # Install Git hooks from .pre-commit-config.yaml using prek
        prek install

        # (Optional but recommended) Run all hooks once on the full codebase
        prek run --all-files
        ```

        After this, hooks will run automatically on each commit.

        ## Alternative setup (pip instead of uv)

        If you prefer plain `pip`, you can set things up like this instead:

        ```bash
        cd <workspace-root>

        # Create a virtual environment
        python -m venv .venv

        # Activate it
        source .venv/bin/activate         # Linux/macOS
        # .venv\\Scripts\\activate        # Windows (PowerShell / CMD)

        # Install the project in editable mode with dev dependencies
        pip install -e .[dev]
        ```

        With `pip`, `prek` will still be available from the virtual environment,
        and you can use the same commands to install hooks:

        ```bash
        prek install
        prek run --all-files
        ```

        ## Next steps

        Open `{target_impl.name}` and implement your custom {ws_type}.

        ## (Optional) Run it as a Service

        You can run your {ws_type} as a Service using the DetectMateService, which is added as
        an optional dependency in the `dev` extras.

        For this, create a settings file (e.g., `service_settings.yaml`) in the workspace root,
        which could look like this:

        ```yaml
        component_name: {name}
        component_type: {impl_module}.{name}
        component_config_class: {impl_module}.{name}Config
        log_level: DEBUG
        log_dir: ./logs
        manager_addr: ipc:///tmp/{name.lower()}_cmd.ipc
        engine_addr: ipc:///tmp/{name.lower()}_engine.ipc
        ```

        Then start your {ws_type} service with:

        ```bash
        detectmate start --settings service_settings.yaml
        ```

        Make sure you run this command from within the virtual environment where you installed
        this workspace (e.g. after `uv venv && source .venv/bin/activate`).
        """
    ).strip() + "\n"

    (target_dir / "README.md").write_text(readme_text)


def create_pyproject(name: str, ws_type: str, target_dir: Path) -> None:
    """Create a minimal pyproject.toml file for the generated workspace.

    - Uses the --name argument (normalized) as the project name.
    - Leaves a dependencies list ready for you to fill with the necessary libraries.
    """

    project_name = normalize(name)

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
        # Treat the '{project_name}' directory as the package
        packages = ["{project_name}"]
        """
    ).strip() + "\n"

    (target_dir / "pyproject.toml").write_text(pyproject_text)
