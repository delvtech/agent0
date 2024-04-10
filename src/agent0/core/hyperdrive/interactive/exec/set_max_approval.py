"""Set the maximum base token approval for a Hyperdrive Agent."""

from __future__ import annotations

import logging

import eth_utils
from web3 import Web3
from web3.contract.contract import Contract

from agent0.core.hyperdrive import HyperdriveAgent
from agent0.ethpy.base import smart_contract_transact


def set_max_approval(
    agent: HyperdriveAgent, web3: Web3, base_token_contract: Contract, hyperdrive_address: str
) -> None:
    """Establish max approval for the hyperdrive contract for the given agent.

    Arguments
    ---------
    agent: HyperdriveAgent
        A Hyperdrive agent to approve.
    web3: Web3
        web3 provider object.
    base_token_contract: Contract
        The deployed ERC20 base token contract.
    hyperdrive_address: str
        The address of the deployed hyperdrive contract.
    """
    try:
        _ = smart_contract_transact(
            web3,
            base_token_contract,
            agent,
            "approve",
            hyperdrive_address,
            eth_utils.conversions.to_int(eth_utils.currency.MAX_WEI),
        )
    except Exception as err:  # pylint: disable=broad-exception-caught
        logging.warning(
            "Base approval failed with exception %s",
            repr(err),
        )
        raise err
