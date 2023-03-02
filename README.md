<div>
  <div>
    <a hre="https://codecov.io/gh/element-fi/elf-simulations">
      <img src="https://codecov.io/gh/element-fi/elf-simulations/branch/main/graph/badge.svg?token=1S60MD42ZP"/>
    </a>
    <a hre="https://github.com/psf/black">
      <img src="https://img.shields.io/badge/code%20style-black-000000.svg"/>
    </a>
    <a hre="https://docs.pytest.org/en/latest/contents.html">
      <img src="https://img.shields.io/badge/testing-pytest-blue.svg"/>
    </a>
  </div>
  <img height="50px" src="https://codecov.io/gh/element-fi/elf-simulations/branch/main/graphs/sunburst.svg?token=1S60MD42ZP">
</div>

# [Element Finance](https://element.fi) market simulation and analysis

This project is a work-in-progress. All code is provided as is and without guarantee.

Documentation can be found [here](https://elfpy.element.fi).

## Install

Set up your favorite python virutal environment with python == 3.8 (we recommend [pyenv](https://github.com/pyenv/pyenv#how-it-works) and [virtualenv](https://github.com/pyenv/pyenv-virtualenv)). While we don't explicitly support python > 3.8, we haven't had trouble running on later versions (with one exception noted below). For example:

```bash
pyenv install 3.8.16
pyenv local 3.8.16
python -m venv .venv
source .venv/bin/activate
```

Once this is done, check that your version is correct when you run `python --version`. Within the virtualenv, upgrade pip with `python -m pip install --upgrade pip` and then install the required packages.

For Python 3.8.16:

```bash
python -m pip install -r requirements-3.8.txt
python -m pip install -e .
```

for Python 3.11:

```bash
python -m pip install -r requirements-3.11.txt
python -m pip install -e .
```

If you intend to improve the documentation, then you must also install the packages in `requirements-dev.txt`.

### Docker

To install a docker development environment which may be more reliable to install project dependencies:

```bash
docker build -t elf-simulations-dev .
```

Then to create an isolated shell environment which observes file changes run:

```bash
docker run -it --name elf-simulations-dev --rm --volume $(pwd):/app/ --net=host elf-simulations-dev:latest bash
```

## Testing

Testing is achieved with [py.test](https://docs.pytest.org/en/latest/contents.html). You can run all tests from the repository root directory by runing `python -m pytest`, or you can pick a specific test in the `tests/` folder with `python -m pytest tests/{test_file.py}`.

## Coverage

To run coverage locally you can follow these steps:

install coverage.py:

```
pip install coverage
```

parse the repo:

```
coverage run --source=elfpy --omit=tests/test_notebooks.py -m unittest discover tests
```

generate the report:

```
coverage xml -i report -m
```

generate html report:

```
coverage xml -i html
```

then just open `htmlcov/index.html` to view the report!

## Apeworks and Contract Integration

[Install Forge](https://github.com/foundry-rs/foundry#installatio://github.com/foundry-rs/foundry#installation)

run:

```
anvil
```

npm link the hyperdrive repo, then run:

```bash
python -m pip install eth-ape==0.5.9
ape plugins list -a
ape plugins install .
ape compile
```

## Examples

Python files in the `examples/` folder should be executable from the repository root. Run them with the -h flag to see argument options. The Jupyter notebooks contained in `examples/notebooks/` should be run locally using [Jupyter](https://jupyter.org/install), [VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks), or something equivalent.

## Contributor git workflow:

We will follow the Rebase workflow that is also used by the Element frontend team.
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
