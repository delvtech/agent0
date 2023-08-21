# Ignore docstrings for this file
# pylint: disable=missing-docstring


import os

import pytest
from chainsync.test_fixtures import database_engine, db_session, dummy_session, psql_docker
from ethpy.test_fixtures import local_chain, local_hyperdrive_chain

# Hack to allow for vscode debugger to throw exception immediately
# instead of allowing pytest to catch the exception and report
# Based on https://stackoverflow.com/questions/62419998/how-can-i-get-pytest-to-not-catch-exceptions/62563106#62563106

# Use this in conjunction with the following launch.json configuration:
#      {
#        "name": "Debug Current Test",
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
if os.getenv("_PYTEST_RAISE", "0") != "0":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value


# Importing all fixtures here and defining here
# This allows for users of fixtures to not have to import all dependency fixtures when running
# TODO this means pytest can only be ran from this directory
__all__ = ["database_engine", "db_session", "dummy_session", "psql_docker", "local_chain", "local_hyperdrive_chain"]
