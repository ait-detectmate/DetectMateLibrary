"""The installed `mate create` console script, run as a subprocess, and the
tests of the workspaces it creates.

What the generated workspace contains is checked in-process in
tests/unit/tools/workspace/test_create_workspace.py.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.cli
@pytest.mark.parametrize("type_, name", [
    ("parser", "MyCoolParser"),
    ("detector", "MyCoolThing"),
    ("alert_aggregator", "MyCoolAlertAggregator"),
])
def test_generated_tests_pass(tmp_path: Path, type_: str, name: str):
    """Run pytest inside the generated workspace on its generated test file."""
    subprocess.check_call(["mate", "create", "--type", type_, "--name", name, "--dir", str(tmp_path)])
    test_file = Path("tests") / f"test_{name}.py"
    assert (tmp_path / test_file).exists()

    # the workspace root must be on sys.path so that the generated package imports
    old_cwd, old_sys_path = os.getcwd(), list(sys.path)
    try:
        os.chdir(tmp_path)
        sys.path.insert(0, str(tmp_path))
        assert pytest.main(["-q", str(test_file)]) == 0
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_sys_path
