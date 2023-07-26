# Install -- overview

Elf-simulations is currently supported only for Python 3.10.

### 1. Install Pyenv

Follow [Pyenv install instructions](https://github.com/pyenv/pyenv#installation).

### 2. Clone Elf-simulations repo

Clone the repo into a <repo_location> of your choice.

```bash
git clone https://github.com/delvtech/elf-simulations.git <repo_location>
```

### 3. Set up virtual environment

Here we use [venv](https://docs.python.org/3/library/venv.html) which is part of the built-in standard Python library. You can use another virtual environment package if you prefer, like [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv).

```bash
cd <repo_location>
pyenv install 3.10
pyenv local 3.10
python -m venv .venv
source .venv/bin/activate
```

### 4. Install Elf-simulations

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade -e ".[with-dependencies]"
```

The dependencies includes postgresql, which is required to work with files in `elfpy/data`.
If you intend to improve the documentation, then you must also install the packages:

```bash
python -m pip install --upgrade -e ".[with-dependencies,docs]"
```

An explanation of what the above steps do:

- `pyenv install 3.10` You should now see the correct version when you run `pyenv versions`.
- `pyenv local 3.10` This command creates a `.python-version` file in your current directory. If you have pyenv active in your environment, this file will automatically activate this version for you.
- `python -m venv .venv` This will create a `.venv` folder in your repo directory that stores the local python build & packages. After this command you should be able to type which python and see that it points to an executable inside `.venv/`.
- `python -m pip install --upgrade -e ".[with-dependencies]"` This installs elfpy locally such that the install updates automatically any time you change the source code. This also installs all dependencies defined in `pyproject.toml`.

## Working with smart contracts (optional)

We run several tests and offer utilities that depend on executing Hyperdrive solidity contracts. This is not required to use elfpy.

NOTE: The Hyperdrive solidity implementation is currently under security review, and thus is not available publicly.
The following instructions will not work for anyone who is not a member of Delv.

### 5. Set up smart contracts

Clone the hyperdrive repo, then create a [sym link](https://en.wikipedia.org/wiki/Symbolic_link#POSIX_and_Unix-like_operating_systems) at `hyperdrive_solidity/` pointing to the repo location.

```bash
git clone git@github.com:delvtech/hyperdrive.git ../hyperdrive
ln -s ../hyperdrive hyperdrive_solidity
```

### 6. Install Hyperdrive pre-requisites

Complete the steps in [Hyperdrive's Pre-requisites section](https://github.com/delvtech/hyperdrive#pre-requisites).

## Notes

You can test that everything is working by calling: `python -m pytest .`

You can test against a local testnet node using [Anvil](<[url](https://book.getfoundry.sh/reference/anvil/)>) with `anvil`.

We use [Docker](docs.docker.com/get-docker) for building images.
