# Install -- overview

All `elf-simulations` packages should be accessed from Python 3.10.
The following outlines our recommended install workflow, although alternatives are listed below.

## 1. Clone the `elf-simulations` repo

Clone the repo into a <repo_location> of your choice.

```bash
git clone git@github.com:delvtech/elf-simulations.git <repo_location>
```

## 2. Install Pyenv

Follow [Pyenv install instructions](https://github.com/pyenv/pyenv#installation).

## 3. Set up a virtual environment

You can use any environment; we use [venv](https://docs.python.org/3/library/venv.html):

```bash
cd <repo_location>
pyenv install 3.10
pyenv local 3.10
python -m venv .venv
source .venv/bin/activate
```

## 4. Install `elf-simulations` packages and requirements

All of the elf-simulations packages can be installed from `requirements.txt`:

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt
```

If you want to use the CI tools, such as run tests, check linting or types, build containers or documentation, then you must also [install Foundry](https://book.getfoundry.sh/getting-started/installation) and the dev packages:

```bash
python -m pip install --upgrade -r requirements-dev.txt
```

Finally, you can test that everything is working by calling: `python -m pytest .`

# Alternate install paths

The default installation directions above should automatically install all local sub-packages, and should be sufficient for development.
We also support these installation options:

## Installing each subpackage independently

After you have cloned the repository you can install each package independently.
For example:

```bash
python -m pip install --upgrade lib/agent0[with-dependencies]
```

Internally, the above installation calls

```bash
pip install agent0[base] # Install with base packages only (this is what's called in requirements.txt)
pip install agent0[lateral] # Installs dependent sub-packages from git (e.g., ethpy)
```

# Working with smart contracts

We run tests and offer utilities that depend on executing bytecode compiled from Hyperdrive solidity contracts.
This is not required to use elfpy.

NOTE: The Hyperdrive solidity implementation is currently under security review, and thus is not available publicly.
The following instructions will not work for anyone who is not a member of Delv.

## 1. Set up smart contracts

Clone the hyperdrive repo:

```bash
git clone git@github.com:delvtech/hyperdrive.git ../hyperdrive
```

## 2. Install Hyperdrive

Complete the steps in Hyperdrive's [Pre-requisites](https://github.com/delvtech/hyperdrive#pre-requisites) and [Build](https://github.com/delvtech/hyperdrive#build) sections.

## 3. Copy ABI & bytecode files
Copy the contract `sol` folders from the generated `out` directory in the `hyperdrive` repository root.
These folder should contain the ABI JSON and bytecode files for each contract.
Paste the folders into `elf-simulations/packages/hyperdrive/src/abis/`.

```bash
cp -R ../hyperdrive/out/*.sol packages/hyperdrive/src/abis/
```

Our codebase uses the following contracts:

```bash
ERC20Mintable.sol/
ERC4626DataProvider.sol/
ERC4626HyperdriveDeployer.sol/
ERC4626HyperdriveFactory.sol/
ForwarderFactory.sol/
IHyperdrive.sol/
MockERC4626.sol/
```

You then can update the generated `hypertypes` python package by running `pypechain` on this folder:

```bash
pip install --upgrade pip && pip install --upgrade pypechain
pypechain packages/hyperdrive/src/abis/ --output_dir lib/hypertypes/hypertypes/
```

# Additional useful applications

You can test against a local testnet node using [Anvil](https://book.getfoundry.sh/reference/anvil/).

We use [Docker](docs.docker.com/get-docker) for building images.
Some tests also use Docker to launch a local postgres server and Anvil chain.
If there are Docker issues when running tests, ensure "Allow the default Docker socket to be used" is set under Advanced settings (typically when running Docker Desktop on Macs).
