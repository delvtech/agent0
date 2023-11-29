# Style guide

- Use [type hints](https://docs.python.org/3/library/typing.html).
- Follow [the PEP8 styleguide](https://peps.python.org/pep-0008/).
  - The only exception: we use a maximum character limit of 120 characters per line.
  - [Black](https://pypi.org/project/black/) and [Pylint](https://pylint.readthedocs.io/en/latest/index.html) will enforce this.
- Write docstrings in [Numpy format](https://numpydoc.readthedocs.io/en/latest/format.html), with a few tweaks:
  - Use "Arguments" instead of "Parameters".
  - Don't use space before `:` in the type specification. Sphinx and VSCode render it the same, and it's closer to the signature.
