[![](https://codecov.io/gh/delvtech/agent0/branch/main/graph/badge.svg?token=1S60MD42ZP)](https://app.codecov.io/gh/delvtech/agent0?displayType=list)
[![](https://readthedocs.org/projects/agent0/badge/?version=latest)](https://agent0.readthedocs.io/en/latest/?badge=latest)
[![](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![](https://img.shields.io/badge/testing-pytest-blue.svg)](https://docs.pytest.org/en/latest/contents.html)
<br><a href="https://app.codecov.io/gh/delvtech/agent0?displayType=list"><img height="50px" src="https://codecov.io/gh/delvtech/agent0/graphs/sunburst.svg?token=1S60MD42ZP"><a>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="icons/agent0-dark.svg">
  <img alt="Agent 0" src="icons/agent0-light.svg">
</picture>

# [DELV](https://delv.tech) repo for market simulation and analysis

This project is a work-in-progress. All code is provided as is and without guarantee.
The language used in this code and documentation is not intended to, and does not, have any particular financial, legal, or regulatory significance.

This docs page can be found via [https://agent0.readthedocs.io/en/latest/](https://agent0.readthedocs.io/en/latest/).

```python
import datetime
from fixedpointmath import FixedPoint
from agent0 import ILocalHyperdrive, ILocalChain

# Initialize
chain = ILocalChain()
interactive_hyperdrive = ILocalHyperdrive(chain)
hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(100_000))

# Run trades
chain.advance_time(datetime.timedelta(weeks=1))
open_long_event = hyperdrive_agent0.open_long(base=FixedPoint(100))
chain.advance_time(datetime.timedelta(weeks=5))
close_event = hyperdrive_agent0.close_long(
    maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
)

# Analyze
pool_state = interactive_hyperdrive.get_pool_state(coerce_float=True)
pool_state.plot(x="block_number", y="longs_outstanding", kind="line")
```

See our [tutorial notebook](examples/tutorial.ipynb) for more information.

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

## Contributions

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## Number format

We frequently use 18-decimal [fixed-point precision numbers](https://github.com/delvtech/fixedpointmath#readme) for arithmetic.
