# Install -- overview

Python 3.9 is required currently, to maintain compatibility with Google Colaboratory.

Set up your favorite python virtual environment. We use:

- [pyenv](https://github.com/pyenv/pyenv#how-it-works) to manage python versions
- [venv](https://docs.python.org/3/library/venv.html) standard library to manage virtual environments

We also use [Docker](docs.docker.com/get-docker) for building images.

# Install -- steps
Clone the repo into a <repo_location> of your choice.
Next, follow the installation instructions provided by [pyenv](https://github.com/pyenv/pyenv#installation).

After installation, we can use pyenv to install Python from within the repo.
```bash
cd <repo_location>
pyenv install 3.9
pyenv local 3.9
python -m venv .venv
source .venv/bin/activate
```
Once you're in your virtual environment, install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```
If you intend to improve the documentation, then you must also install the packages in `requirements-dev.txt`.

* `pyenv install 3.9` You should now see the correct version when you run `pyenv versions`.
* `pyenv local 3.9` This command creates a `.python-version` file in your current directory. If you have pyenv active in your environment, this file will automatically activate this version for you.
* `python -m venv .venv` This will create a `.venv` folder in your repo directory that stores the local python build & packages. After this command you should be able to type which python and see that it points to an executable inside `.venv/`.
* `python -m pip install -e .` This installs elfpy locally such that the install updates automatically any time you change the source code. 

Finally, you can test that everything is working by calling:
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/`

## Apeworks and Contract Integration

We run several tests and offer utilities that depend on executing Hyperdrive solidity contracts. This is not required to use elfpy.

NOTE: The Hyperdrive solidity implementation is currently under security review, and thus is not available publicly.
The following instructions will not work for anyone who is not a member of Delv.

First, [install Forge](https://github.com/foundry-rs/foundry#installatio://github.com/foundry-rs/foundry#installation).

Next, to use apeworx with elfpy, clone and sym link the hyperdrive repo, into `hyperdrive_solidity/`, i.e.:

```bash
git clone https://github.com/delvtech/hyperdrive.git ../hyperdrive
ln -s ../hyperdrive hyperdrive_solidity
```

then run:

```bash
ape plugins install .
ape compile
```

You should now be able to test that everything is working with `pytest .`

NOTE: These steps also set you up to run a local blockchain instance without Docker. To do so, you can run `ape compile -v DEBUG` to compile the hyperdrive repo without optimizations. You'll need to repreat this command any time you change a Hyperdrive solidity file. Then to start the service run `anvil --port [PREFERRED-PORT] --block-time [SECONDS-PER-BLOCK] --host 0.0.0.0`, where you fill in the commands you need. For example `8549` for the port and `12` for the seconds per block.

NOTE: `pip` might complain about dependency incompatibility between eth-ape and some plugins. This discrepancy comes from apeworx, although our examples should run without dealing with the incompatibility.
