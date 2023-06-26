# Install -- overview

Elf-simulations has been tested with Python 3.9 and 3.10.

1. Install Pyenv

Follow [Pyenv install instructions](https://github.com/pyenv/pyenv#installation).

2. Clone Elf-simulations repo

Clone the repo into a <repo_location> of your choice, i.e. `git clone https://github.com/delvtech/elf-simulations.git <repo_location>`

3. Set up virtual environment.

```bash
cd <repo_location>
pyenv install 3.10
pyenv local 3.10
python -m venv .venv
source .venv/bin/activate
```

4. Install Elf-simulations.

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade -e ".[with-dependencies]"
```

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

5. Set up smart contracts

Clone and sym link the hyperdrive repo, into `hyperdrive_solidity/`, i.e.:

```bash
git clone https://github.com/delvtech/hyperdrive.git ../hyperdrive
ln -s ../hyperdrive hyperdrive_solidity
```

6. Install Hyperdrive pre-requisites

Complete the steps in [Hyperdrive's Pre-requisites section](https://github.com/delvtech/hyperdrive#pre-requisites).

7. Install ape plugins

Install Ape plugins with `ape plugins install .`

## Notes

You can test that everything is working by calling: `python -m pytest .`

You can test against a local testnet node using [Anvil]([url](https://book.getfoundry.sh/reference/anvil/)) with `anvil`.

NOTE: `pip` might complain about dependency incompatibility between eth-ape and some plugins. This discrepancy comes from apeworx, although our examples should run without dealing with the incompatibility.
