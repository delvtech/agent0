[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![testing: pytest](https://img.shields.io/badge/testing-pytest-blue.svg)](https://docs.pytest.org/en/latest/contents.html)
[![license: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-lightgrey)](http://www.apache.org/licenses/LICENSE-2.0)
[![DELV - Terms of Service](https://img.shields.io/badge/DELV-Terms_of_Service-orange)](https://elementfi.s3.us-east-2.amazonaws.com/element-finance-terms-of-service.pdf)

[![testing: coverage](https://codecov.io/gh/delvtech/agent0/branch/main/graph/badge.svg?token=1S60MD42ZP)](https://app.codecov.io/gh/delvtech/agent0?displayType=list)
[![docs: build](https://readthedocs.org/projects/agent0/badge/?version=latest)](https://agent0.readthedocs.io/en/latest/?badge=latest)
<br><a href="https://app.codecov.io/gh/delvtech/agent0?displayType=list"><img height="50px" src="https://codecov.io/gh/delvtech/agent0/graphs/sunburst.svg?token=1S60MD42ZP"><a>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="icons/agent0-dark.svg">
  <img alt="Agent 0" src="icons/agent0-light.svg">
</picture>

# [DELV](https://delv.tech) repo for market simulation and analysis

This docs page can be found via [https://agent0.readthedocs.io/en/latest/](https://agent0.readthedocs.io/en/latest/).

## Quickstart

This repo contains general purpose code for interacting with Ethereum smart contracts.
However, it was bulit for the primary use case of trading on [Hyperdrive](https://hyperdrive.delv.tech) markets.
Below is an example for executing Hyperdrive trades in a simulated blockchain environment:

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

See our [tutorial notebook](examples/tutorial.ipynb) for more information, including details on executing trades on remote chains.

## Install

Install via pip: `pip install agent0`

Please refer to [INSTALL.md](INSTALL.md) for more advanced install options.

## Deployment

Please refer to [BUILD.md](BUILD.md).

## Testing

We deploy a local anvil chain to run system tests.
Therefore, you must [install foundry](https://github.com/foundry-rs/foundry#installatio://github.com/foundry-rs/foundry#installation) as a prerequisite for running tests.

Testing is achieved with [py.test](https://docs.pytest.org/en/latest/contents.html).
You can run all tests from the repository root directory by running `python -m pytest`, or you can pick a specific test with `python -m pytest {path/to/test_file.py}`.
General integration-level tests are in the `tests` folder, while more isolated or unit tests are colocated with the files they are testing and end with a `_test.py` suffix.

## Contributions

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## Coverage

To run coverage locally you can follow these steps:

```bash
pip install coverage
coverage run -m pytest
coverage html
```

then just open `htmlcov/index.html` to view the report!

## Number format

We frequently use 18-decimal [fixed-point precision numbers](https://github.com/delvtech/fixedpointmath#readme) for arithmetic.

## Disclaimer

This project is a work-in-progress.
The language used in this code and documentation is not intended to, and does not, have any particular financial, legal, or regulatory significance.

---

Copyright © 2024  DELV

Licensed under the Apache License, Version 2.0 (the "OSS License").

By accessing or using this code, you signify that you have read, understand and agree to be bound by and to comply with the [OSS License](http://www.apache.org/licenses/LICENSE-2.0) and [DELV's Terms of Service](https://elementfi.s3.us-east-2.amazonaws.com/element-finance-terms-of-service.pdf). If you do not agree to those terms, you are prohibited from accessing or using this code.

Unless required by applicable law or agreed to in writing, software distributed under the OSS License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the OSS License and the DELV Terms of Service for the specific language governing permissions and limitations.
