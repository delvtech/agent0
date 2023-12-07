"""Runs all fuzz tests forever."""
from __future__ import annotations

import sys

import rollbar
from hyperlogs.rollbar_utilities import initialize_rollbar

from agent0.hyperdrive.interactive.chain import LocalChain
from agent0.interactive_fuzz import (
    fuzz_hyperdrive_balance,
    fuzz_long_short_maturity_values,
    fuzz_path_independence,
    fuzz_profit_check,
)


def main():
    """Runs all fuzz tests"""
    initialize_rollbar("interactivefuzz")

    num_trades = 10
    num_paths_checked = 10

    while True:
        try:
            chain_config = LocalChain.Config(db_port=5433, chain_port=10000)
            fuzz_hyperdrive_balance(num_trades, chain_config)
        except AssertionError:
            rollbar.report_exc_info(sys.exc_info(), "error", payload={})

        try:
            chain_config = LocalChain.Config(db_port=5434, chain_port=10001)
            fuzz_long_short_maturity_values(num_trades, chain_config)
        except AssertionError:
            rollbar.report_exc_info(sys.exc_info(), "error", payload={})

        try:
            chain_config = LocalChain.Config(db_port=5435, chain_port=10002)
            fuzz_path_independence(num_trades, num_paths_checked, chain_config)
        except AssertionError:
            rollbar.report_exc_info(sys.exc_info(), "error", payload={})

        try:
            chain_config = LocalChain.Config(db_port=5436, chain_port=10003)
            fuzz_profit_check(chain_config)
        except AssertionError:
            rollbar.report_exc_info(sys.exc_info(), "error", payload={})


if __name__ == "__main__":
    main()