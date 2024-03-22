"""Set the maximum base token approval for a Hyperdrive Agent."""

from __future__ import annotations

import logging

import eth_utils
from web3 import Web3
from web3.contract.contract import Contract

from agent0.core.hyperdrive import HyperdriveAgent
from agent0.ethpy.base import smart_contract_transact


def set_max_approval(
    agent: HyperdriveAgent, web3: Web3, base_token_contract: Contract, hyperdrive_address: str, retry_count: int = 5
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
    retry_count: int, optional
        The number of attempts to make for the smart contract transaction.
        Defaults to 5.
    """
    success = False
    exception = None
    for attempt in range(retry_count):
        try:
            _ = smart_contract_transact(
                web3,
                base_token_contract,
                agent,
                "approve",
                hyperdrive_address,
                eth_utils.conversions.to_int(eth_utils.currency.MAX_WEI),
            )
            success = True
        except Exception as err:  # pylint: disable=broad-exception-caught
            logging.warning(
                "Retry attempt %s out of %s: Base approval failed with exception %s",
                attempt,
                retry_count,
                repr(err),
            )
            exception = err
            success = False

        # If successful, break retry loop
        if success:
            break

    if not success and exception:
        raise exception
