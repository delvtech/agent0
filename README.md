[![](https://codecov.io/gh/delvtech/agent0/branch/main/graph/badge.svg?token=1S60MD42ZP)](https://app.codecov.io/gh/delvtech/agent0?displayType=list)
[![](https://readthedocs.org/projects/agent0/badge/?version=latest)](https://agent0.readthedocs.io/en/latest/?badge=latest)
[![](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![](https://img.shields.io/badge/testing-pytest-blue.svg)](https://docs.pytest.org/en/latest/contents.html)
<br><a href="https://app.codecov.io/gh/delvtech/agent0?displayType=list"><img height="50px" src="https://codecov.io/gh/delvtech/agent0/graphs/sunburst.svg?token=1S60MD42ZP"><a>

# [DELV](https://delv.tech) monorepo for market simulation and analysis

This project is a work-in-progress. All code is provided as is and without guarantee.
The language used in this code and documentation is not intended to, and does not, have any particular financial, legal, or regulatory significance.

This docs page can be found via [https://agent0.readthedocs.io/en/latest/](https://agent0.readthedocs.io/en/latest/).

## Packages

This monorepo houses internal packages that are still under development. They are:

- agent0 ([README](lib/agent0/README.md))
- chainsync ([README](lib/chainsync/README.md))
- ethpy ([README](lib/ethpy/README.md))

We also utilize internal packages that are "in production," which is to say they live in their own repo:

- pypechain ([README](https://github.com/delvtech/pypechain/tree/main#readme), [pypi](https://pypi.org/project/pypechain/))
- fixedpointmath ([README](https://github.com/delvtech/fixedpointmath#readme), [pypi](https://pypi.org/project/fixedpointmath/))

## Install

Please refer to [INSTALL.md](INSTALL.md).

## Deployment

Please refer to [BUILD.md](BUILD.md).

## Testing

We deploy a local anvil chain to run system tests. Therefore, you must [install foundry](https://github.com/foundry-rs/foundry#installatio://github.com/foundry-rs/foundry#installation) as a prerequisite for running tests.

Testing is achieved with [py.test](https://docs.pytest.org/en/latest/contents.html). You can run all tests from the repository root directory by running `python -m pytest`, or you can pick a specific test in the `tests/` folder with `python -m pytest tests/{test_file.py}`.

## Coverage

To run coverage locally you can follow these steps:

```bash
pip install coverage
coverage run -m pytest
coverage html
```

then just open `htmlcov/index.html` to view the report!

## Examples

Python files in the `examples/` folder should be executable from the repository root.
Run them with the -h flag to see argument options.
The Jupyter notebooks contained in `examples/notebooks/` should be run locally using [Jupyter](https://jupyter.org/install), [VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks), or something equivalent.

## Contributions

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## Modifying configuration for agent deployment

Follow [`lib/agent0/README.md`](lib/agent0/README.md) for agent deployment.

## Data pipeline

The data pipeline queries the running chain and exports data to a postgres database. The `infra` repository spins up a local postgres instance via Docker, and the data pipeline will point to this by default. Optionally, you can also configure the backend database by specifying the following environmental variables (for example, in a `.env` file in the base of the repo):

```bash
POSTGRES_USER="admin"
POSTGRES_PASSWORD="password"
POSTGRES_DB="postgres_db"
POSTGRES_HOST="localhost"
POSTGRES_PORT=5432
```

The data script can be then ran using the following command:

```bash
python lib/chainsync/chainsync/exec/acquire_data.py
```

## Number format

We frequently use 18-decimal [fixed-point precision numbers](https://github.com/delvtech/fixedpointmath#readme) for arithmetic.
