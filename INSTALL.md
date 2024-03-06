# Install -- overview

`agent0` requires Python 3.10.

## 1. Clone the `agent0` repo

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

## 3. Install `agent0` packages and requirements


```bash
uv venv .venv -p 3.10
source .venv/bin/activate
uv pip install --upgrade agent0@.
# For an editable install, we can point it to the current directory
# uv pip install -e .
uv pip install -r requirements-hyperdrivepy.txt
```

If you want to use the CI tools, such as run tests, check linting or types, build containers or documentation, then you must also [install Foundry](https://book.getfoundry.sh/getting-started/installation). Additionally, you must replace the agent0 install above with the optional `[dev]` dependency.

```bash
uv pip install --upgrade agent0[dev]@.
# uv pip install -e .[dev]
```

## 4. Install auxillary dependencies for Interactive Hyperdrive

Agent0 provides a fully managed simulator via Interactive Hyperdrive that requires several auxillary dependencies to be installed. Specifically, we require [Foundry](https://book.getfoundry.sh/getting-started/installation), which we use to run the Anvil local testnet node, as well as [docker](https://docs.docker.com/engine/install/) for hosting the node and a database.

Finally, you can test that everything is working by calling: `python -m pytest .`