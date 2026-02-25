import argparse
import shutil
import sys
from pathlib import Path

from .utils import create_readme, create_pyproject, normalize_package_name

# resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent  # tools/
PROJECT_ROOT = BASE_DIR.parent.parent  # root of project
TEMPLATE_DIR = BASE_DIR / "workspace" / "templates"

META_FILES = ["LICENSE.md", ".gitignore", ".pre-commit-config.yaml"]
DATA_FILES = {
    "parser": "src/tools/workspace/templates/data/logs.json",
    "detector": "src/tools/workspace/templates/data/parsed_log.json"
}


def copy_file(src: Path, dst: Path) -> None:
    """Copy file while ensuring destination directory exists."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def camelize(name: str) -> str:
    """Convert names like "custom_parser" or "customParser" to
    "CustomParser"."""
    if "_" in name or "-" in name:
        parts = name.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts if p)
    return name[0].upper() + name[1:]


def create_tests(type_: str, name: str, workspace_root: Path, pkg_name: str) -> None:
    """Create a tests/ directory with a basic pytest file for the component.

    - Reads template tests from src/tools/workspace/templates/test_templates/
    - Rewrites the import to point to <pkg_name>.<name>
    - Renames CustomParser/CustomDetector to the camelized class name
    """

    tests_dir = workspace_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    template_file = TEMPLATE_DIR / "test_templates" / f"test_Custom{type_.capitalize()}.py"
    test_file = tests_dir / f"test_{name}.py"

    if not template_file.exists():
        print(f"WARNING: Test template {template_file} not found. Creating empty test file.", file=sys.stderr)
        test_file.touch()
        return

    template_content = template_file.read_text()
    base_class = f"Custom{type_.capitalize()}"  # base names in the template (CustomParser/CustomDetector)
    # The exact import line in the template, e.g:
    # from ..CustomParser import CustomParser, CustomParserConfig
    # from ..CustomDetector import CustomDetector, CustomDetectorConfig
    original_import = f"from ..{base_class} import {base_class}, {base_class}Config"
    new_class = camelize(name)
    # new import line for the generated workspace:
    # from <pkg_name>.<name> import <NewClass>, <NewClass>Config
    new_import = f"from {pkg_name}.{normalize_package_name(name)} import {new_class}, {new_class}Config"
    # replace the import line
    content = template_content.replace(original_import, new_import)
    # replace the remaining occurrences of CustomParser/CustomDetector
    # with the new class name (inside the tests)
    content = content.replace(base_class, new_class)
    content = content.rstrip() + "\n"

    test_file.write_text(content)
    print(f"- Added tests file: {test_file}")


def create_workspace(type_: str, name: str, target_dir: Path) -> None:
    """Main workspace creation logic.

    - `target_dir` is the workspace root (from --dir)
    - Code lives in a subpackage: <target_dir>/<name>/
    - Meta files (LICENSE, .gitignore, etc.) + README.md + pyproject.toml live in workspace root
    """

    # Workspace root
    workspace_root = Path(target_dir).expanduser().resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)

    # Package directory inside the workspace
    pkg_name = normalize_package_name(name)
    pkg_dir = workspace_root / pkg_name

    # Fail if the package directory already exists
    if pkg_dir.exists():
        print(f"ERROR: Target directory already exists: {pkg_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Creating workspace at: {pkg_dir}")
    pkg_dir.mkdir(parents=True, exist_ok=False)

    # Template selection
    template_file = TEMPLATE_DIR / f"Custom{type_.capitalize()}.py"
    module_name = normalize_package_name(name)
    target_code_file = pkg_dir / f"{module_name}.py"

    if not template_file.exists():
        print(f"WARNING: Template not found: {template_file}. Creating empty file.", file=sys.stderr)
        target_code_file.touch()
    else:
        template_content = template_file.read_text()

        # Replace default class name inside template
        original_class = f"Custom{type_.capitalize()}"
        new_class = camelize(name)
        template_content = template_content.replace(original_class, new_class)

        target_code_file.write_text(template_content)

    print(f"- Added implementation file: {target_code_file}")

    # Make the package importable
    (pkg_dir / "__init__.py").touch()

    create_tests(type_=type_, name=name, workspace_root=workspace_root, pkg_name=pkg_name)

    # Copy data
    copy_file(PROJECT_ROOT / DATA_FILES[type_], workspace_root / "data.json")

    # Copy meta/root files
    for file_name in META_FILES:
        src = PROJECT_ROOT / file_name
        dst = workspace_root / file_name

        if src.exists():
            copy_file(src, dst)
            print(f"- Copied {file_name}")
        else:
            print(f"! Warning: {file_name} not found in project root.")

    # Create pyproject.toml
    create_pyproject(name, type_, workspace_root)
    print(f"- Created pyproject.toml in {workspace_root}")

    # Create README
    create_readme(name, type_, target_code_file, workspace_root)
    print(f"- Created README.md in {workspace_root}")
    print("\nWorkspace created successfully!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new workspace")

    subparsers = parser.add_subparsers(dest="command", required=True)
    create_cmd = subparsers.add_parser("create", help="Create a workspace")

    create_cmd.add_argument(
        "--type",
        required=True,
        choices=["parser", "detector"],
        help="Type of component to generate",
    )

    create_cmd.add_argument(
        "--name",
        required=True,
        help="Name for the generated file (e.g., customParser)",
    )

    create_cmd.add_argument(
        "--dir",
        required=True,
        help="Directory where the workspace will be created",
    )

    args = parser.parse_args()

    if args.command == "create":
        target_dir = Path(args.dir).expanduser().resolve()
        create_workspace(args.type, args.name, target_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
