# Documentation

We strive for verbose and readable comments and docstrings.
Our documentation follows the [Numpy format](https://numpydoc.readthedocs.io/en/latest/format.html).
The hosted docs are automatically generated using [Sphinx](https://www.sphinx-doc.org/en/master/tutorial/automatic-doc-generation.html).

## Contributor git workflow:

We follow a standard [feature branch rebase workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow) that prioritizes short PRs with isolated improvements.
Commits to `main` should **only** be made in the form of squash-merges from pull requests.
For example,

```bash
git checkout feature-branch
git add [files to be committed]
git commit -m 'Change summary'
```

_later, some new commits show up in main, so we rebase our branch_

```bash
git pull --rebase origin main
git push -f feature-branch
```

_now, we have completed our feature, so we create a PR to merge the branch into main_

Once the PR is approved, we perform a final rebase, if necessary, and then a _squash merge_. This means each PR results in a single commit to `main`.

If two people are working in a branch then you should `git pull --rebase origin feature-branch` _before_ `git push origin feature-branch`.
We also recommend that you start each working session with a `pull` and end it with a `push`, so that your colleagues can work asynchronously while you are not.
