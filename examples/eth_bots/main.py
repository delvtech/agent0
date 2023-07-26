"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

from eth_typing import BlockNumber

from examples.eth_bots.setup_experiment import setup_experiment
from examples.eth_bots.trade_loop import trade_if_new_block


def main():
    """Entrypoint to load all configurations and run agents."""
    # exposing the base_token_contract for debugging purposes.
    # pylint: disable=unused-variable
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
