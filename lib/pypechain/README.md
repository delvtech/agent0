# Pypechain

Static python bindings for ethereum smart contracts.

- Parses JSON ABI's to create typesafe web3.py contract instances
- Functions have typesafe function parameters and return values
- Smart Contract internal types are exposed as dataclasses

### Install

See toplevel INSTALL.md

### Usage

From lib/pypecahin, run:

```bash
#  python pypechain/run_pypechain.py <ABI_FILE>          <OUT_FILE>
❯❯ python pypechain/run_pypechain.py './abis/ERC20.json' './build/ERC20Contract.py'
```

Much of this is subject to change as more features are fleshed out.
