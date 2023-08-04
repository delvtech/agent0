"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
import warnings

from eth_typing import BlockNumber

from elf_simulations.eth_bots.core.setup_experiment import setup_experiment
from elf_simulations.eth_bots.core.trade_loop import trade_if_new_block


def main():
    """Entrypoint to load all configurations and run agents."""
    # exposing the base_token_contract for debugging purposes.
    # pylint: disable=unused-variable
    # sane defaults to avoid spam from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")
    web3, hyperdrive_contract, base_token_contract, environment_config, agent_accounts = setup_experiment()
    last_executed_block = BlockNumber(0)
    while True:
        last_executed_block = trade_if_new_block(
            web3,
            hyperdrive_contract,
            agent_accounts,
            environment_config.halt_on_errors,
            last_executed_block,
        )


if __name__ == "__main__":
    main()
