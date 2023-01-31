[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![testing: pytest](https://img.shields.io/badge/testing-pytest-blue.svg)](https://docs.pytest.org/en/latest/contents.html)

# [Element Finance](https://element.fi) market simulation and analysis

This project is a work-in-progress. All code is provided as is and without guarantee.

## Install

Set up your favorite [python virutal environment](https://github.com/pyenv/pyenv#how-it-works) with python >= 3.10 (note additional command required for 3.11, not guaranteed to work due to the `stochastic` package having a <3.11 pythond dependency, but it's been working for us in testing).

Within the [virtualenv](https://github.com/pyenv/pyenv-virtualenv), upgrade pip with `python3 -m pip install --upgrade pip` and then install the required packages.

for Python 3.10, this is sufficient:

```bash
python -m pip install -r requirements.txt
```

for Python 3.11, an extra step is required:

```bash
python -m pip install stochastic --ignore-requires-python
python -m pip install -r requirements.txt
```

Then install the elfpy package with `python3 -m pip install -e .` from the git directory root.

### Docker

To install a docker development environment which may be more reliable to install project dependencies:

``` bash
docker build -t elf-simulations-dev .
```

Then to create an isolated shell environment which observes file changes run:

``` bash
docker run -it --name elf-simulations-dev --rm --volume $(pwd):/app/ --net=host elf-simulations-dev:latest bash
```

## Testing

Testing is achieved with [py.test](https://docs.pytest.org/en/latest/contents.html). You can run all tests from the repository root directory by runing `python3 -m pytest`, or you can pick a specific test in the `tests/` folder with `python3 -m pytest tests/{test_file.py}`.

## Examples

Python files in the `examples/` folder should be executable from the repository root. Run them with the -h flag to see argument options. The Jupyter notebooks contained in `examples/notebooks/` should be run locally using [Jupyter](https://jupyter.org/install), [VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks), or something equivalent. We do not recommend using Google Colab because the install process requires upgrading the Colab Python version to 3.10 and pip installing elfpy from the git URI.

## Contributor git workflow:

We will follow the Rebase workflow that is used by the Element frontend team.
Commits to `main` should **only** be made in the form of squash merges from pull requests.
For example,

```bash
git checkout feature-branch
git add [files to be committed]
git commit -m 'Complete change summary'
```

_later, some new commits show up in main, so we rebase our branch_

```bash
git pull --rebase origin main
git push feature-branch
```

_now, we have completed our feature, so we create a PR to merge the branch into main_

Once the PR is approved, we perform a final rebase, if necessary, and then a _squash merge_. This means each PR results in a single commit to `main`.

If two people are working in a branch then you should `git pull --rebase origin feature-branch` _before_ `git push origin feature-branch`. We also recommend that you start each working session with a `pull` and end it with a `push`, so that your colleagues can work asynchronously while you are not.
