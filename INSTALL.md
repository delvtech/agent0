# Install -- overview

`Agent0` requires Python 3.10.

## 1. Clone the `agent0` monorepo

Clone the repo into a <repo_location> of your choice, then enter that directory.

```bash
git clone https://github.com/delvtech/agent0.git <repo_location>
cd <repo_location>
```

## 2. Install uv

We use [uv](https://github.com/astral-sh/uv) for package management and virtual environments.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3. Install `agent0` in a virtual environment

```bash
uv venv .venv -p 3.10
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

If you want to use the CI tools, such as run tests, check linting or types, build containers or documentation, then you must also [install Foundry](https://book.getfoundry.sh/getting-started/installation) and the dev packages:

```bash
python -m pip install --upgrade -r requirements-dev.txt
```

Finally, you can test that everything is working by calling: `python -m pytest .`

# Working with smart contracts

We run tests and offer utilities that depend on executing bytecode compiled from Hyperdrive solidity contracts.
This is not required to use the agent0 libraries.

NOTE: The Hyperdrive solidity implementation is currently under security review, and thus is not available publicly.
The following instructions will not work for anyone who is not a member of Delv.

## 1. Set up smart contracts

Clone the hyperdrive repo:

```bash
git clone git@github.com:delvtech/hyperdrive.git ../hyperdrive
```

## 2. Install and Build Hyperdrive

Complete the steps in Hyperdrive's [Pre-requisites](https://github.com/delvtech/hyperdrive#pre-requisites) and [Build](https://github.com/delvtech/hyperdrive#build) sections.

## 3. Copy ABI & bytecode files

Copy the contract `sol` folders from the generated `out` directory in the `hyperdrive` repository root.
These folder should contain the ABI JSON and bytecode files for each contract.
Paste the folders into `agnet0/packages/hyperdrive/src/abis/`.

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
IERC4626Hyperdrive.sol/
IHyperdrive.sol/
MockERC4626.sol/
```

You then can update the generated `hypertypes` python package by running `pypechain` on this folder:

```bash
pip install --upgrade pip && pip install --upgrade pypechain
pypechain packages/hyperdrive/src/abis/ --output-dir lib/hypertypes/hypertypes/types/
```

# Additional useful applications

You can test against a local testnet node using [Anvil](https://book.getfoundry.sh/reference/anvil/).

We use [Docker](docs.docker.com/get-docker) for building images.
Some tests also use Docker to launch a local postgres server and Anvil chain.
If there are Docker issues when running tests, ensure "Allow the default Docker socket to be used" is set under Advanced settings (typically when running Docker Desktop on Macs).
