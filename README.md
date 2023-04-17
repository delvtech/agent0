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

Python 3.9 is required currently, to maintain compatibility with Google Colaboratory.

Set up your favorite python virtual environment. We use:

- [pyenv](https://github.com/pyenv/pyenv#how-it-works) to manage python versions
- [venv](https://docs.python.org/3/library/venv.html) standard library to manage virtual environments

Then run:

```bash
pyenv install 3.9
pyenv local 3.9
python -m venv .venv
source .venv/bin/activate
```

Once you're in your favored virtual environment, install the project dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

If you intend to improve the documentation, then you must also install the packages in `requirements-dev.txt`.

### Docker

Using Docker is mostly untested, as the core team doesn't use it. However, the following steps should get you started.

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

```bash
pip install coverage
coverage run -m pytest
coverage html
```

then just open `htmlcov/index.html` to view the report!

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

## Apeworks and Contract Integration

NOTE: The Hyperdrive solidity implementation is currently under security review, and thus is not available publicly.
The following instructions will not work for anyone who is not a member of Element Finance.

[Install Forge](https://github.com/foundry-rs/foundry#installatio://github.com/foundry-rs/foundry#installation)

You can optionally run

```
anvil
```

if you wish to execute ape against a local foundry backend. To use apeworx with elfpy, clone and sym link the hyperdrive repo, into `hyperdrive_solidity/`, i.e.:

```bash
git clone https://github.com/element-fi/hyperdrive.git ../hyperdrive
ln -s ../hyperdrive hyperdrive_solidity
```

then run:

```bash
cp ape-config.yaml.example ape-config.yaml
pip install eth-ape
ape plugins install .
ape compile
```

NOTE: `pip` might complain about dependency incompatibility between eth-ape and some plugins. This discrepancy comes from apeworx, although our examples should run without dealing with the incompatibility.
