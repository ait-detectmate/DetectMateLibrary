import os
import sys
import subprocess
import pytest
from pathlib import Path
from tools.workspace.utils import normalize_package_name


# Path to the CLI entry point
CLI = ["mate"]  # installed as console script


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    # Creates an isolated directory for each test (workspace root)
    return tmp_path


def test_create_parser_workspace(temp_dir: Path):
    ws_name = "myParser"
    workspace_root = temp_dir
    pkg_name = normalize_package_name(ws_name)  # myparser
    module_name = normalize_package_name(ws_name)  # myparser
    pkg_dir = workspace_root / pkg_name
    tests_dir = workspace_root / "tests"

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
    assert (workspace_root / "data.json").exists()

    # Python files live in package directory
    py_files = list(pkg_dir.glob("*.py"))
    assert len(py_files) == 2  # __init__.py + myParser.py
    assert (pkg_dir / f"{module_name}.py").exists()
    assert (pkg_dir / "__init__.py").exists()
    assert tests_dir.exists()
    assert (tests_dir / f"test_{ws_name}.py").exists()


def test_create_detector_workspace(temp_dir: Path):
    ws_name = "myDetector"
    workspace_root = temp_dir
    pkg_name = normalize_package_name(ws_name)  # mydetector
    module_name = normalize_package_name(ws_name)  # mydetector
    pkg_dir = workspace_root / pkg_name
    tests_dir = workspace_root / "tests"

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
    assert (pkg_dir / f"{module_name}.py").exists()
    assert (pkg_dir / "__init__.py").exists()
    assert tests_dir.exists()
    assert (tests_dir / f"test_{ws_name}.py").exists()


def test_create_workspace_with_dash_name(temp_dir: Path):
    ws_name = "custom-parser"
    workspace_root = temp_dir
    pkg_name = normalize_package_name(ws_name)  # custom_parser
    module_name = normalize_package_name(ws_name)  # custom_parser
    pkg_dir = workspace_root / pkg_name
    tests_dir = workspace_root / "tests"
    test_file = tests_dir / f"test_{ws_name}.py"

    subprocess.check_call([
        *CLI,
        "create",
        "--type", "parser",
        "--name", ws_name,
        "--dir", str(workspace_root),
    ])

    assert workspace_root.exists()
    assert pkg_dir.exists()
    assert tests_dir.exists()
    assert test_file.exists()
    assert (pkg_dir / "__init__.py").exists()
    assert (pkg_dir / f"{module_name}.py").exists()

    # check that the generated test imports use the normalized names
    content = test_file.read_text()
    print(content)
    assert f"from {pkg_name}.{module_name} import " in content


def test_fail_if_dir_exists(temp_dir: Path):
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


def test_generated_detector_tests_pass(temp_dir: Path):
    """Run pytest inside the generated workspace on the generated detector test
    file."""

    ws_name = "MyCoolThing"
    workspace_root = temp_dir
    pkg_dir = workspace_root / "mycoolthing"
    tests_dir = workspace_root / "tests"
    test_file = tests_dir / f"test_{ws_name}.py"

    subprocess.check_call([
        *CLI,
        "create",
        "--type", "detector",
        "--name", ws_name,
        "--dir", str(workspace_root),
    ])

    assert workspace_root.exists()
    assert pkg_dir.exists()
    assert tests_dir.exists()
    assert test_file.exists()

    # run pytest on the generated test file
    # and make sure the workspace root is on sys.path so "import mycoolthing" works
    old_cwd = os.getcwd()
    old_sys_path = list(sys.path)
    try:
        os.chdir(workspace_root)
        sys.path.insert(0, str(workspace_root))
        result = pytest.main(["-q", str(test_file.relative_to(workspace_root))])
        assert result == 0
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_sys_path


def test_generated_parser_tests_pass(temp_dir: Path):
    ws_name = "MyCoolParser"
    workspace_root = temp_dir
    pkg_dir = workspace_root / "mycoolparser"
    tests_dir = workspace_root / "tests"
    test_file = tests_dir / f"test_{ws_name}.py"

    subprocess.check_call([
        *CLI,
        "create",
        "--type", "parser",
        "--name", ws_name,
        "--dir", str(workspace_root),
    ])

    assert workspace_root.exists()
    assert pkg_dir.exists()
    assert tests_dir.exists()
    assert test_file.exists()

    old_cwd = os.getcwd()
    old_sys_path = list(sys.path)
    try:
        os.chdir(workspace_root)
        sys.path.insert(0, str(workspace_root))
        result = pytest.main(["-q", str(test_file.relative_to(workspace_root))])
        assert result == 0
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_sys_path
