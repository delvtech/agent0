# Contributing to agent0

## Documentation

We strive for verbose and readable comments and docstrings.
All code and documentation should follow our [style guide](STYLEGUIDE.md).
The hosted docs are automatically generated using [Sphinx](https://www.sphinx-doc.org/en/master/tutorial/automatic-doc-generation.html).

## Contributor git workflow

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

Once the PR is approved, we perform a final rebase, if necessary, and then a _squash merge_.
This means each PR results in a single commit to `main`.
Please provide a brief description of the PR in the summary, as opposed to a list of commit strings.

## Building with new Hyperdrive contracts
If you wish to incporporate modifications made to the Hyperdrive contracts, you must update agent0 by:

- Add the new version tag to `src/agent0/hyperdrive.version`.
- Replace the Solidity contract ABIs in `packages/hyperdrive/src/abis` with the newly compiled files from Hyperdrive.
- Run `pypechain packages/hyperdrive/src/abis/ --output-dir=src/agent0/hypertypes/types`

## Contributing a new bot policy

We welcome contributions of new bot policies, alongside those in `src/agent0/core/hyperdrive/policies`.

Submit a pull request that meets the following criteria:

1. Do something an existing policy doesn't already accomplish
2. Be well-documented and follow our existing [STYLEGUIDE.md](STYLEGUIDE.md).
3. Pass all linting and type checks (the GH actions will check this for you).
4. Describe the bot's behavior in a `describe` [classmethod](https://docs.python.org/3/library/functions.html#classmethod) similarly to existing bots, ending in a `super().describe()` call.

## Publishing a release

For code owners who wish to publish a release, make sure to follow these guidelines:

1. Merge a PR that edits `pyproject.toml` to specify the new semver version.
2. From the updated `main` branch, make a new tag with `git tag vX.Y.Z`.
3. Push that tag to the remote repository with `git push --tags`.
4. Go to the `releases` tab in Github and add the new tag as a release.
5. Click the "Generate Release Notes" button to generate release notes.
6. Add a brief summary under the "What's Changed" heading and create a "PRs" heading for the generated list of "PRs".
