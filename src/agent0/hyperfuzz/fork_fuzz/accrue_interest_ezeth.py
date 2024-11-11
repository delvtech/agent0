"""Function to accrue interest in the ezeth pool when fork fuzzing."""

from __future__ import annotations

from fixedpointmath import FixedPoint, FixedPointIntegerMath
from hyperdrivetypes.types import IDepositQueueContract, IRestakeManagerContract
from pypechain.core.contract_call_exception import check_txn_receipt
from web3 import Web3
from web3.types import RPCEndpoint, TxParams, Wei

from agent0.ethpy.base import get_account_balance, set_account_balance
from agent0.ethpy.hyperdrive import HyperdriveReadWriteInterface

SECONDS_IN_YEAR = 365 * 24 * 60 * 60

# Contract addresses for mainnet fork
RESTAKE_MANAGER_ADDR = "0x74a09653A083691711cF8215a6ab074BB4e99ef5"
DEPOSIT_QUEUE_ADDR = "0xf2F305D14DCD8aaef887E0428B3c9534795D0d60"


def accrue_interest_ezeth(
    interface: HyperdriveReadWriteInterface, variable_rate: FixedPoint, block_number_before_advance: int
) -> None:
    """Function to accrue interest in the ezeth pool when fork fuzzing.

    Arguments
    ---------
    interface: HyperdriveReadWriteInterface
        The interface to the Hyperdrive pool.
    variable_rate: FixedPoint
        The variable rate of the pool.
    block_number_before_advance: int
        The block number before time was advanced.
    """
    # pylint: disable=too-many-locals

    assert variable_rate > FixedPoint(0)

    # TODO we may want to build these objects once and store them
    restake_manager = IRestakeManagerContract.factory(w3=interface.web3)(Web3.to_checksum_address(RESTAKE_MANAGER_ADDR))
    deposit_queue = IDepositQueueContract.factory(w3=interface.web3)(Web3.to_checksum_address(DEPOSIT_QUEUE_ADDR))
    # TODO we probably just want to do this once
    response = interface.web3.provider.make_request(
        method=RPCEndpoint("anvil_impersonateAccount"), params=[RESTAKE_MANAGER_ADDR]
    )
    # ensure response is valid
    if "result" not in response:
        raise KeyError("Response did not have a result.")

    # There's a current issue with pypechain where it breaks if the called function returns a double nested list,
    # e.g., in calculateTVLs. We fall back to using pure web3 for this.
    # https://github.com/delvtech/pypechain/issues/147
    previous_total_tvl = FixedPoint(
        scaled_value=restake_manager.get_function_by_name("calculateTVLs")().call(
            block_identifier=block_number_before_advance
        )[2]
    )
    previous_timestamp = interface.get_block_timestamp(interface.get_block(block_number_before_advance))
    current_timestamp = interface.get_block_timestamp(interface.get_block("latest"))
    time_delta = current_timestamp - previous_timestamp

    adjusted_variable_rate = FixedPoint(
        scaled_value=FixedPointIntegerMath.mul_div_down(variable_rate.scaled_value, time_delta, SECONDS_IN_YEAR)
    )

    eth_to_add = previous_total_tvl * adjusted_variable_rate

    # Give eth to restake manager
    curr_balance = FixedPoint(scaled_value=get_account_balance(interface.web3, RESTAKE_MANAGER_ADDR))
    _ = set_account_balance(
        interface.web3,
        RESTAKE_MANAGER_ADDR,
        # Give a little bit extra for gas
        (curr_balance + eth_to_add + FixedPoint(0.01)).scaled_value,
    )

    # TODO we need a "transact and wait" function in pypechain, as we don't need to sign due to impersonation
    tx_func = deposit_queue.functions.depositETHFromProtocol()
    tx_hash = tx_func.transact(TxParams({"from": RESTAKE_MANAGER_ADDR, "value": Wei(eth_to_add.scaled_value)}))
    tx_receipt = interface.web3.eth.wait_for_transaction_receipt(tx_hash)
    check_txn_receipt(tx_func, tx_hash, tx_receipt)
