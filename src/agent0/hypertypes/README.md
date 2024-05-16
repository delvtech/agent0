# Updating hyperdrive contracts

We run tests and offer utilities that depend on executing bytecode compiled from Hyperdrive solidity contracts. These are the steps for updating all dependencies on the underlying hyperdrive contracts.

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
Paste the folders into `agent0/packages/hyperdrive/src/abis/`.

Our codebase uses the following contracts:

```bash
ERC20ForwarderFactory.sol
ERC20Mintable.sol
ERC4626HyperdriveCoreDeployer.sol
ERC4626HyperdriveDeployerCoordinator.sol
ERC4626Target0Deployer.sol
ERC4626Target1deployer.sol
ERC4626Target2Deployer.sol
ERC4626Target3Deployer.sol
HyperdriveFactory.sol
HyperdriveRegistry.sol
IHyperdrive.sol
LPMath.sol
MockERC4626.sol
```

You then can update the generated `hypertypes` python package by running `pypechain` on this folder:

```bash
pip install --upgrade pip && pip install --upgrade pypechain
pypechain packages/hyperdrive/src/abis/ --output-dir src/agent0/hypertypes/types/
```