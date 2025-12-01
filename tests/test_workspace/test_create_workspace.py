import subprocess
import pytest

# Path to the CLI entry point
CLI = ["mate"]  # installed as console script


@pytest.fixture
def temp_dir(tmp_path):
    # Creates an isolated directory for each test (workspace root)
    return tmp_path


def test_create_parser_workspace(temp_dir):
    ws_name = "myParser"
    workspace_root = temp_dir
    pkg_dir = workspace_root / ws_name

    # Run the CLI tool
    subprocess.check_call([
        *CLI,
        "create",
        "--type", "parser",
        "--name", ws_name,
        "--dir", str(workspace_root),
    ])

    # Workspace root exists
    assert workspace_root.exists()

    # Package directory exists
    assert pkg_dir.exists()

    # Meta files live in workspace root
    assert (workspace_root / "LICENSE.md").exists()
    assert (workspace_root / ".gitignore").exists()
    assert (workspace_root / ".pre-commit-config.yaml").exists()
    assert (workspace_root / "README.md").exists()

    # Python files live in package directory
    py_files = list(pkg_dir.glob("*.py"))
    assert len(py_files) == 2  # __init__.py + myParser.py
    assert (pkg_dir / f"{ws_name}.py").exists()
    assert (pkg_dir / "__init__.py").exists()


def test_create_detector_workspace(temp_dir):
    ws_name = "myDetector"
    workspace_root = temp_dir
    pkg_dir = workspace_root / ws_name

    subprocess.check_call([
        *CLI,
        "create",
        "--type", "detector",
        "--name", ws_name,
        "--dir", str(workspace_root),
    ])

    assert workspace_root.exists()
    assert pkg_dir.exists()

    assert (workspace_root / "LICENSE.md").exists()
    assert (workspace_root / ".gitignore").exists()
    assert (workspace_root / ".pre-commit-config.yaml").exists()
    assert (workspace_root / "README.md").exists()

    py_files = list(pkg_dir.glob("*.py"))
    assert len(py_files) == 2  # __init__.py + myDetector.py
    assert (pkg_dir / f"{ws_name}.py").exists()
    assert (pkg_dir / "__init__.py").exists()


def test_fail_if_dir_exists(temp_dir):
    ws_name = "existing"
    workspace_root = temp_dir
    pkg_dir = workspace_root / ws_name

    # Pre-create the package directory to force failure
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Should fail because the package directory already exists
    result = subprocess.run([
        *CLI,
        "create",
        "--type", "parser",
        "--name", ws_name,
        "--dir", str(workspace_root),
    ], capture_output=True, text=True)

    assert result.returncode != 0
    assert "already exists" in result.stderr
