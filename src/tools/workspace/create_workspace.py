import argparse
import shutil
import sys
from pathlib import Path

from .utils import create_readme, create_pyproject, normalize

# resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent  # tools/
PROJECT_ROOT = BASE_DIR.parent.parent  # root of project
TEMPLATE_DIR = BASE_DIR / "workspace" / "templates"

META_FILES = ["LICENSE.md", ".gitignore", ".pre-commit-config.yaml"]


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
    pkg_dir = workspace_root / normalize(name)

    # Fail if the package directory already exists
    if pkg_dir.exists():
        print(f"ERROR: Target directory already exists: {pkg_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Creating workspace at: {pkg_dir}")
    pkg_dir.mkdir(parents=True, exist_ok=False)

    # Template selection
    template_file = TEMPLATE_DIR / f"Custom{type_.capitalize()}.py"
    target_code_file = pkg_dir / f"{name}.py"

    if not template_file.exists():
        print(f"WARNING: Template not found: {template_file}. Creating empty file.",
              file=sys.stderr)
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
