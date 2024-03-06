[![](https://codecov.io/gh/delvtech/agent0/branch/main/graph/badge.svg?token=1S60MD42ZP)](https://app.codecov.io/gh/delvtech/agent0?displayType=list)
[![](https://readthedocs.org/projects/agent0/badge/?version=latest)](https://agent0.readthedocs.io/en/latest/?badge=latest)
[![](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![](https://img.shields.io/badge/testing-pytest-blue.svg)](https://docs.pytest.org/en/latest/contents.html)
<br><a href="https://app.codecov.io/gh/delvtech/agent0?displayType=list"><img height="50px" src="https://codecov.io/gh/delvtech/agent0/graphs/sunburst.svg?token=1S60MD42ZP"><a>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="icons/agent0-dark.svg">
  <img alt="Agent 0" src="icons/agent0-light.svg">
</picture>

# [DELV](https://delv.tech) monorepo for market simulation and analysis

This project is a work-in-progress. All code is provided as is and without guarantee.
The language used in this code and documentation is not intended to, and does not, have any particular financial, legal, or regulatory significance.

This docs page can be found via [https://agent0.readthedocs.io/en/latest/](https://agent0.readthedocs.io/en/latest/).

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
The Jupyter notebook `examples/tutorial.ipynb` should be run locally using [Jupyter](https://jupyter.org/install), [VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks), or something equivalent.

## Contributions

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## Modifying configuration for agent deployment

Follow [`lib/agent0/README.md`](lib/agent0/README.md) for agent deployment.

## Number format

We frequently use 18-decimal [fixed-point precision numbers](https://github.com/delvtech/fixedpointmath#readme) for arithmetic.
