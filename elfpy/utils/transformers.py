"""Library to transform from elf-sims to Ape objects."""
from ape.contracts.base import ContractTransaction
from ethpm_types.abi import MethodABI
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy


def trade_details_to_abi(trade_details, hyperdrive_instance, account) -> tuple[ContractTransaction, tuple, MethodABI]:
    """Convert trade_details to abi call."""
    # build params kwargs to pass to ape_trade
    params = {
        "trade_type": trade_details.action_type.name,
        "hyperdrive_contract": hyperdrive_instance,
        "agent": account,
        "amount": trade_details.trade_amount.scaled_value,  # ape works with ints
    }
    if trade_details.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
        params["maturity_time"] = int(trade_details.mint_time + elfpy.SECONDS_IN_YEAR)

    # show that we can return whichever part of the "abi call" you want, without executing it!
    contract_txn: ContractTransaction
    args: tuple
    abi: MethodABI
    contract_txn, args, abi = ape_utils.create_trade(**params)
    return contract_txn, args, abi
