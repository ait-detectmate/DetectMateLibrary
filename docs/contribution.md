# Contributing

We welcome patches and other contributions.

## Bug reports and enhancement requests

We track bug reports and enhancement requests in GitHub Issues. Before opening an issue, check whether someone has already reported it. Add any new details to the existing issue. Include the following information in a bug report.

1. Description of the bug. Describe the problem clearly.
2. Steps to reproduce. A minimal code snippet, plus the configuration (YAML or dict) and, if
   possible, a few log lines that trigger the problem.
3. Expected behavior. What should happen, and what happens instead (including the full error
   message, if any)?
4. Environment. Your Python version, your DetectMate version
   (`python -c "import detectmatelibrary; print(detectmatelibrary.__version__)"`) and your
   operating system.

*Please don't include any private/sensitive information in your issue! For reporting security-related issues, see [SECURITY.md](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/SECURITY.md)*

## Working on the codebase

To contribute to this project, you must fork the project and create a pull request to the upstream repository.

### 1. Fork

Sign in to GitHub, open the repository, and click **Fork**. [DetectMateLibrary](https://github.com/ait-detectmate/DetectMateLibrary)

### 2. Clone

After forking the repository into your own workspace, clone the development branch of that repository.

```console title="Clone repository"
git clone -b development git@github.com:YOURUSERNAME/DetectMateLibrary.git
```

!!! note

    If the `development` branch is deleted, a GitHub Action automatically recreates it from `main`.

### 3. Create a feature branch

Create a feature branch for each work item and give it a descriptive name.

```console title="Create branch"
cd DetectMateLibrary
git checkout -b feature-some_important_work
```

### 4. Develop your feature in the feature branch

Keep your commits focused on the work item for this branch.

### 5. Fetch and merge from the upstream

When your work is ready, synchronize your branch with the upstream `development` branch.

```console title="Fetch and merge"
git remote add upstream git@github.com:ait-detectmate/DetectMateLibrary.git
git pull upstream development
```

If conflicts occur, resolve them, stage the changes with `git add`, and continue the merge.

Further reading

- [https://www.atlassian.com/git/tutorials/merging-vs-rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing)
- [https://www.atlassian.com/git/tutorials/merging-vs-rebasing#the-golden-rule-of-rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing#the-golden-rule-of-rebasing)
- [https://dev.to/toogoodyshoes/mastering-rebasing-and-fast-forwarding-in-git-2j19](https://dev.to/toogoodyshoes/mastering-rebasing-and-fast-forwarding-in-git-2j19)

### 6. Push the changes to your GitHub repository

Review your commits before pushing.

```console title="Get logs"
git log
```

Use interactive rebase to squash related commits. For example, this command lets you squash the last two commits.

```console title="Rebase"
git rebase -i HEAD~2
```

Push the changes to your GitHub repository.

```console title="Push"
git push
```

Additional documentation:

- [https://www.atlassian.com/git/tutorials/merging-vs-rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing)

### 7. Submit your pull request

Open a pull request on GitHub and target `ait-detectmate/DetectMateLibrary`.

After the pull request merges into `development`, continue to step 8. To address review feedback, make the requested changes and squash the follow-up commits before pushing.

```console title="Rebase head again"
git rebase -i HEAD~2
```

Delete your local feature branch after the pull request merges into `development`.

### 8. Update your local development branch

Update your local development branch:

```console title="Update branch"
git fetch upstream development
git checkout development
git rebase upstream/development
```

Further reading

- [https://www.atlassian.com/git/tutorials/merging-vs-rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing)

### 9. Update the development branch in your GitHub repository

After updating your local `development` branch in step 8, push it to your GitHub repository.

```console title="Push again"
git push
```
