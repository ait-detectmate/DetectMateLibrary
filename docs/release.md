# Release Process

This document describes the steps to publish a new release of `DetectMateLibrary`.

## Keeping dependencies up to date

Dependency updates via Dependabot do not require a full release. If only Dependabot PRs are pending and no feature work needs to go out, merge them into `main` and then merge `main` back into `development` to keep both branches in sync.

To merge `main` into `development` using the GitHub UI:

1. Go to the repository on GitHub and click **Pull requests**, then **New pull request**.
2. Set the **base** branch to `development` and the **compare** branch to `main`.
3. Click **Create pull request**, add a short title (e.g. `Merge main into development`), and submit.
4. Once CI passes, merge the PR.

## Prerequisites

Before starting a release, make sure all work intended for this version has been merged into the `development` branch and that CI is passing.

## Steps

### 1. Merge Dependabot PRs into main

Review any open Dependabot pull requests and merge the relevant ones into `main` before continuing.

### 2. Merge development into main

Open a pull request to merge the `development` branch into `main`. Once CI passes and the PR is approved, merge it.

!!! note

    Merging `development` into `main` will delete the `development` branch. A GitHub Action (`recreate-development-branch.yml`) automatically recreates it from `main` right after deletion, so no manual step is needed.

### 3. Determine the new version number

`DetectMateLibrary` follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

- **Patch** (`0.3.x`): bug fixes, updates/correction to documentation and dependabot updates.
- **Minor** (`0.x.0`): new features with backwards-compatible functionality. No breaking changes. Reset the patch number to `0`.
- **Major** (`x.0.0`): breaking changes. Reset both minor and patch numbers to `0`.

### 4. Bump the version number

Create a new branch from `main` and update the version string in `src/detectmatelibrary/metadata.py`:

```python
__version__ = "0.X.Y"  # set to the new release version
```

The version here must match the tag you will create in step 5 (e.g. version `0.4.0` corresponds to tag `v0.4.0`).

Also make sure `uv.lock` is up to date:

```bash
uv lock
```

Commit any changes, push the branch, and open a pull request against `main`. Once CI passes, merge it.

### 5. Create a GitHub release

Go to the [Releases page](https://github.com/ait-detectmate/DetectMateLibrary/releases) and click **Draft a new release**.

- Set the tag to `vX.Y.Z` (e.g. `v0.4.0`), targeting the `main` branch. GitHub will create the tag on publish.
- Set the release title to the version string (e.g. `v0.4.0`).
- Click **Generate release notes** to populate the changelog automatically.
- Review the generated release notes and adjust if needed.
- Click **Publish release**.

### 6. Check automatically triggered workflows

Publishing the release triggers the following GitHub Actions workflows automatically:

- **Publish Docs** (`publish-docs.yml`): deploys a new versioned copy of the documentation and updates the `latest` alias.
- **Upload Python Package** (`python-publish.yml`): builds and publishes the new package version to PyPI.

Monitor the [Actions tab](https://github.com/ait-detectmate/DetectMateLibrary/actions) to confirm all workflows complete successfully.

The `development` branch was already recreated automatically in step 2 and is ready for the next iteration of work.
