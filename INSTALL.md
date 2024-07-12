# Install

## 1. Prerequisites

- [Docker](https://docs.docker.com/engine/install/) for hosting the underlying data tools.
- [Foundry](https://book.getfoundry.sh/getting-started/installation) for running a local Anvil testnnet node for simulations.

Additionally, `agent0` uses the package [`hyperdrivepy`](https://pypi.org/project/hyperdrivepy/) as a dependency. `hyperdrivepy` contains
prebuilt binaries for common environments. However, if your environment is not supported, pip will attempt to build from
the distributed source distribution, which requires [Rust](https://www.rust-lang.org/tools/install) installed in your
environment to compile. Ensure you are using rustc 1.78.0-nightly or newer when building from source distribution.

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
