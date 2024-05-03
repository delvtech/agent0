# Ignore docstrings for this file
# pylint: disable=missing-docstring
# ruff: noqa: D100 (undocumented-public-module)


import os

import pytest

from agent0.chainsync.test_fixtures import database_engine, db_session, dummy_session, psql_docker
from agent0.core.test_utils import cycle_trade_policy
from agent0.test_fixtures import (
    chain_fixture,
    fast_chain_fixture,
    fast_hyperdrive_fixture,
    hyperdrive_fixture,
    hyperdrive_read_interface_fixture,
    hyperdrive_read_write_interface_fixture,
    init_chain,
    init_hyperdrive,
)

# Hack to allow for vscode debugger to throw exception immediately
# instead of allowing pytest to catch the exception and report
# Based on https://stackoverflow.com/questions/62419998/how-can-i-get-pytest-to-not-catch-exceptions/62563106#62563106

# IMPORTANT NOTE!!!!!
# If you end up using this debugging method, this will catch exceptions before teardown of fixtures
# This means that the local postgres fixture (which launches a docker container) will not automatically
# be cleaned up if you, e.g., use the debugger and a db test fails. Make sure to manually clean up.
# TODO maybe automatically close the container on catch here
# TODO this seems to happen sometimes, not all the time, track down

# Use this in conjunction with the following launch.json configuration:
#      {
#        "name": "Debug Current Test",
#        "type": "python",
#        "request": "launch",
#        "module": "pytest",
#        "args": ["${file}", "-vs"],
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
# NOTE: this means pytest can only be ran from this directory
__all__ = [
    "fast_chain_fixture",
    "chain_fixture",
    "init_chain",
    "fast_hyperdrive_fixture",
    "hyperdrive_fixture",
    "init_hyperdrive",
    "cycle_trade_policy",
    "database_engine",
    "db_session",
    "dummy_session",
    "hyperdrive_read_interface_fixture",
    "hyperdrive_read_write_interface_fixture",
    "psql_docker",
]
