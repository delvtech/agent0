[![](https://codecov.io/gh/delvtech/elf-simulations/branch/main/graph/badge.svg?token=1S60MD42ZP)](https://app.codecov.io/gh/delvtech/elf-simulations?displayType=list)
[![](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![](https://img.shields.io/badge/testing-pytest-blue.svg)](https://docs.pytest.org/en/latest/contents.html)
<br><a href="https://app.codecov.io/gh/delvtech/elf-simulations?displayType=list"><img height="50px" src="https://codecov.io/gh/delvtech/elf-simulations/branch/main/graphs/sunburst.svg?token=1S60MD42ZP"><a>

# [DELV](https://delv.tech) market simulation and analysis

This project is a work-in-progress. All code is provided as is and without guarantee.
The language used in this code and documentation is not intended to, and does not, have any particular financial, legal, or regulatory significance.

Documentation can be found [here](https://elfpy.delv.tech).

## Install

Please refer to [INSTALL.md](https://github.com/delvtech/elf-simulations/blob/main/INSTALL.md).

## Deployment

Please refer to [BUILD.md](https://github.com/delvtech/elf-simulations/blob/main/BUILD.md).

## Testing

Testing is achieved with [py.test](https://docs.pytest.org/en/latest/contents.html). You can run all tests from the repository root directory by runing `python -m pytest`, or you can pick a specific test in the `tests/` folder with `python -m pytest tests/{test_file.py}`.

## Coverage

To run coverage locally you can follow these steps:

```bash
pip install coverage
coverage run -m pytest
coverage html
```

then just open `htmlcov/index.html` to view the report!

## Examples

Python files in the `examples/` folder should be executable from the repository root. Run them with the -h flag to see argument options. The Jupyter notebooks contained in `examples/notebooks/` should be run locally using [Jupyter](https://jupyter.org/install), [VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks), or something equivalent.

## Contributions

Please refer to [CONTRIBUTING.md](https://github.com/delvtech/elf-simulations/blob/main/CONTRIBUTING.md).

## Number format

Internally Elfpy conducts all operations using 18-decimal fixed-point precision integers and arithmetic.
Briefly, this means our representation for unity, "one", is `1 * 10 ** 18`, which would be `1.0` when cast to a float.

This can lead to confusion when additionally dealing with standard Python floats and ints.
As such, we have purposefully constrain support for mixed-type operations that include the FixedPoint type.
Due to a lack of known precision, operations against Python floats are not allowed (e.g. `float * FixedPoint` will raise an error).
However, operations against `int` are allowed.
In this case, the `int` _argument_ is assumed to be "unscaled", i.e. if you write `int(8) * FixedPoint(8)` we will scale up the first variable return a `FixedPoint` number that represents the float `64.0` in 18-decimal FixedPoint format.
So in this example the internal representation of that operation would be `64*10**18`.
If you cast FixedPoint numbers to ints or floats you will get "unscaled" representation, e.g. `float(FixedPoint(8.0)) == 8.0` and `int(FixedPoint(8.528)) == 8`.

If you want the integer scaled representation, which can be useful for communicating with Solidity contracts, you must ask for it explicitly, e.g. `FixedPoint(8.52).scaled_value == 8520000000000000000`.
Conversely, if you want to initialize a FixedPoint variable using the scaled integer representation, then you need to instantiate the variable using the `scaled_value` argument, e.g. `FixedPoint(scaled_value=8)`.
In that example, the internal representation is `8`, so casting it to a float would produce a small value: `float(FixedPoint(scaled_value=8)) == 8e-18`.

To understand more, we recommend that you study the fixed point tests and source implementation in `elfpy/math/`.

## Modifying configuration for bot deployment
Bots can be deployed using the `evm_bots.py` script in the examples folder.
If you wish to run it with non-default parameters, then you must specify them as a JSON file.
To generate a default configuration file, from the base directory, run:

```bash
python elfpy/bots/bots_default_config.py
```

This will generate `bots_config.default.json`, which you can feed into `evm_bots.py`:

```bash
evm_bots.py bots_config.default.json
```

## Data pipeline
The data pipeline queries the running chain and exports data to a postgres database. The `infra` repostitory spins up a local postgres instance via Docker, and the data piepline will point to this by default. Optinally, you can also configure the backend database by specifying the following environmental variables (for example, in a `.env` file in the base of the repo):

```bash
POSTGRES_USER="admin"
POSTGRES_PASSWORD="password"
POSTGRES_DB="postgres_db"
POSTGRES_HOST="localhost"
POSTGRES_PORT=5432
```

The data script can be then ran using the following command:

```bash
python elfpy/data/acquire_data.py
```
