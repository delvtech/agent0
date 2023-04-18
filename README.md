<div>
  <div>
    <a hre="https://codecov.io/gh/element-fi/elf-simulations">
      <img src="https://codecov.io/gh/element-fi/elf-simulations/branch/main/graph/badge.svg?token=1S60MD42ZP"/>
    </a>
    <a hre="https://github.com/psf/black">
      <img src="https://img.shields.io/badge/code%20style-black-000000.svg"/>
    </a>
    <a hre="https://docs.pytest.org/en/latest/contents.html">
      <img src="https://img.shields.io/badge/testing-pytest-blue.svg"/>
    </a>
  </div>
  <img height="50px" src="https://codecov.io/gh/element-fi/elf-simulations/branch/main/graphs/sunburst.svg?token=1S60MD42ZP">
</div>

# [DELV](https://delv.tech) market simulation and analysis

This project is a work-in-progress. All code is provided as is and without guarantee.

Documentation can be found [here](https://elfpy.delv.tech).

## Install

Please refer to [INSTALL.md](https://github.com/element-fi/elf-simulations/blob/main/INSTALL.md).

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

Please refer to [CONTRIBUTING.md](https://github.com/element-fi/elf-simulations/blob/main/INSTALL.md).

## Number format

Internally Elfpy conducts all operations using 18-decimal fixed-point precision integers and arithmetic.
Briefly, this means our representation for unity, "one", is `1 * 10 ** 18`.
This can create confusion when additionally dealing with standard Python floats and ints.
As such, we have purposefully constrained support for mixed-type operations that include the FixedPoint type (e.g. `int * FixedPoint` is not allowed).
This may change as we continue to develop our workflow.
To understand more, we recommend that you study the fixed point tests and source implementation.
