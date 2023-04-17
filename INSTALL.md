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
python -m pip install -r requirements.txt
python -m pip install -e .
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
