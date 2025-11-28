import argparse
import shutil
from pathlib import Path

# resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent  # tools/
PROJECT_ROOT = BASE_DIR.parent.parent  # root of project
TEMPLATE_DIR = BASE_DIR / "workspace" / "templates"


def copy_file(src: Path, dst: Path):
    """Copy file while ensuring destination directory exists."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)


def create_readme(target_dir: Path, name: str, type_: str):
    """Generate a template README.md"""
    content = f"""# {name}

This is a custom **{type_}** workspace generated with:
mate create --type {type_} --name {name} --dir {target_dir}

## Structure

- `{name}.py`: Your custom {type_} implementation.
- `LICENSE.md`: Copied from the main project.
- `.gitignore`: Copied from the main project.
- `.pre-commit-config.yaml`: Copied from the main project.

## Next Steps

Implement your {type_} logic inside `{name}.py`  
and integrate it with the main system.
"""
    with open(target_dir / "README.md", "w") as f:
        f.write(content)


def create_workspace(type_: str, name: str, target_dir: Path):
    """Main workspace creation logic."""

    print(f"Creating workspace at: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy template code
    template_file = TEMPLATE_DIR / f"Custom{type_.capitalize()}.py"
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")

    target_code_file = target_dir / f"{name}.py"
    copy_file(template_file, target_code_file)
    print(f"- Added template code: {target_code_file}")

    # Copy root files
    root_files = ["LICENSE.md", ".gitignore", ".pre-commit-config.yaml"]

    for file_name in root_files:
        src = PROJECT_ROOT / file_name
        dst = target_dir / file_name
        if src.exists():
            copy_file(src, dst)
            print(f"- Copied {file_name}")
        else:
            print(f"! Warning: {file_name} not found in project root.")

    # Create README
    create_readme(target_dir, name, type_)
    print(f"- Created README.md")

    print("\nWorkspace created successfully!")


def main():
    parser = argparse.ArgumentParser(description="Create a new workspace")

    subparsers = parser.add_subparsers(dest="command")
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
