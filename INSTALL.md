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

You may need to install [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation).
Refer to the [suggested build environment](https://github.com/pyenv/pyenv/wiki#suggested-build-environment) if you see
warnings that system packages are not installed.

Use [venv](https://docs.python.org/3/library/venv.html) to create a local virual Python environment:

```bash
cd <repo_location>
pyenv install 3.10
pyenv local 3.10
python -m venv --upgrade-deps .venv
source .venv/bin/activate
```

## 4. Install `agent0`

```bash
pip install --upgrade pip
pip install -e .
# pip install . # For non-editable install
# pip install -e '.[dev]' # For dev and testing tools
# pip install -e '.[all]' # Install everything
```

## 5. Verify

You can test that everything is working by calling `python -m pytest .`
