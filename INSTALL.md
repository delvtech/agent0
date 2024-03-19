# Install

## 1. Prerequisites
While not strictly required when connecting to a remote chain, we recommend that you install these tools to use the full suite of Agent0 simulation tools.

- [Foundry](https://book.getfoundry.sh/getting-started/installation) for running a local Anvil testnnet node.
- [Docker](https://docs.docker.com/engine/install/) for hosting the underlying data tools.

## 2. Clone
Clone the repo to <repo_location>, then enter that directory.

```bash
git clone https://github.com/delvtech/agent0.git <repo_location>
cd <repo_location>
```

## 3. Setup environment
We use [uv](https://github.com/astral-sh/uv) for package management and virtual environments.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv -p 3.10
source .venv/bin/activate
```

## 4. Install `agent0`
```bash
uv pip install -e .
# uv pip install agent0@. # For non-editable install
# uv pip install -e '.[dev]' # For dev and testing tools
# uv pip install -e '.[all]' # Install everything
```

## 5. Verify

You can test that everything is working by calling `python -m pytest .`
