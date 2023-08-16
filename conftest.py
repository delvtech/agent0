# Hack to allow for vscode debugger to throw exception immediately
# instead of allowing pytest to catch the exception and report
# Use this in conjunction with the following launch.json configuration:
#      {
#        "name": "Debug Tests",
#        "type": "python",
#        "request": "launch",
#        "module": "pytest",
#        "args": ["${file}"],
#        "console": "integratedTerminal",
#        "justMyCode": true,
#        "env": {
#            "_PYTEST_RAISE": "1"
#        },
#      },

# Ignore docstrings for this file
# pylint: disable=missing-docstring


import os

import pytest

if os.getenv("_PYTEST_RAISE", "0") != "0":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value
