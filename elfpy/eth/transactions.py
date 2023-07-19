"""Web3 powered functions for interfacing with smart contracts"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from web3 import Web3
from web3.contract.contract import Contract, ContractFunction
from web3.types import ABI, ABIFunctionComponents, ABIFunctionParams, TxReceipt

from .accounts import EthAccount


def smart_contract_read(contract: Contract, function_name: str, *fn_args, **fn_kwargs) -> dict[str, Any]:
    """Return from a smart contract read call

    .. todo::
        function to recursively find component names & types
        function to dynamically assign types to output variables
            would be cool if this also put stuff into FixedPoint
    """
    # get the callable contract function from function_name & call it
    function: ContractFunction = contract.get_function_by_name(function_name)(*fn_args)  # , **fn_kwargs)
    return_values = function.call(**fn_kwargs)
    if not isinstance(return_values, Sequence):  # could be list or tuple
        return_values = [return_values]
    if contract.abi:  # not all contracts have an associated ABI
        return_names_and_types = _contract_function_abi_outputs(contract.abi, function_name)
        if return_names_and_types is not None:
            if len(return_names_and_types) != len(return_values):
                raise AssertionError(
                    f"{len(return_names_and_types)=} must equal {len(return_values)=}."
                    f"\n{return_names_and_types=}\n{return_values=}"
                )
            function_return_dict = {}
            for var_name_and_type, var_value in zip(return_names_and_types, return_values):
                var_name = var_name_and_type[0]
                if var_name:
                    function_return_dict[var_name] = var_value
                else:
                    function_return_dict["value"] = var_value
            return function_return_dict
    return {f"value{idx}": value for idx, value in enumerate(return_values)}


def smart_contract_transact(
    web3: Web3, contract: Contract, signer: EthAccount, function_name_or_signature: str, *fn_args
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    contract : Contract
        any compiled web3 contract
    function_name : str
        this function must exist in the compiled contract's ABI
    from_account : EthAccount
        the EthAccount that will be used to pay for the gas & sign the transaction
    fn_args : unordered list
        all remaining arguments will be passed to the contract function in the order received

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    try:
        if "(" in function_name_or_signature:
            func_handle = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
        else:
            func_handle = contract.get_function_by_name(function_name_or_signature)(*fn_args)
        unsent_txn = func_handle.build_transaction(
            {
                "from": signer.checksum_address,
                "nonce": web3.eth.get_transaction_count(signer.checksum_address),
            }
        )
        signed_txn = signer.account.sign_transaction(unsent_txn)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        # wait for approval to complete
        return web3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as err:
        print(f"{err=}")
        print(f"{function_name_or_signature=}")
        print(f"{fn_args=}")
        raise err

        # logging.error()


def _get_name_and_type_from_abi(abi_outputs: ABIFunctionComponents | ABIFunctionParams) -> tuple[str, str]:
    """Retrieve and narrow the types for abi outputs"""
    return_value_name: str | None = abi_outputs.get("name")
    if return_value_name is None:
        return_value_name = "none"
    return_value_type: str | None = abi_outputs.get("type")
    if return_value_type is None:
        return_value_type = "none"
    return (return_value_name, return_value_type)


def _contract_function_abi_outputs(contract_abi: ABI, function_name: str) -> list[tuple[str, str]] | None:
    """Parse the function abi to get the name and type for each output"""
    function_abi = None
    # find the first function matching the function_name
    for abi in contract_abi:  # loop over each entry in the abi list
        if abi.get("name") == function_name:  # check the name
            function_abi = abi  # pull out the one with the desired name
            break
    if function_abi is None:
        logging.warning("could not find function_name=%s in contract abi", function_name)
        return None
    function_outputs = function_abi.get("outputs")
    if function_outputs is None:
        logging.warning("function abi does not specify outputs")
        return None
    if not isinstance(function_outputs, Sequence):  # could be list or tuple
        logging.warning("function abi outputs are not a sequence")
        return None
    if len(function_outputs) > 1:  # multiple unnamed vars were returned
        return_names_and_types = []
        for output in function_outputs:
            return_names_and_types.append(_get_name_and_type_from_abi(output))
    if (
        function_outputs[0].get("type") == "tuple" and function_outputs[0].get("components") is not None
    ):  # multiple named outputs were returned in a struct
        abi_components = function_outputs[0].get("components")
        if abi_components is None:
            logging.warning("function abi output componenets are not a included")
            return None
        return_names_and_types = []
        for component in abi_components:
            return_names_and_types.append(_get_name_and_type_from_abi(component))
    else:  # final condition is a single output
        return_names_and_types = [_get_name_and_type_from_abi(function_outputs[0])]
    return return_names_and_types


# TODO: either make a lookup table for these or decode automatically when we see a CustomContractError
# ##################
# ### Hyperdrive ###
# ##################
# BaseBufferExceedsShareReserves: 0x18846de9
# InvalidApr: 0x76c22a22
# InvalidBaseToken: 0x0e442a4a
# InvalidCheckpointTime: 0xecd29e81
# InvalidInitialSharePrice: 0x55f2a42f
# InvalidMaturityTime: 0x987dadd3
# InvalidPositionDuration: 0x4a7fff9e
# InvalidFeeAmounts: 0x45ee5986
# NegativeInterest: 0x512095c7
# OutputLimit: 0xc9726517
# Paused: 0x9e87fac8
# PoolAlreadyInitialized: 0x7983c051
# TransferFailed: 0x90b8ec18
# UnexpectedAssetId: 0xe9bf5433
# UnsupportedToken: 0x6a172882
# ZeroAmount: 0x1f2a2005
# ZeroLpTotalSupply: 0x252c3a3e
# ZeroLpTotalSupply: 0x252c3a3e

# ############
# ### TWAP ###
# ############
# QueryOutOfRange: 0xa89817b0

# ####################
# ### DataProvider ###
# ####################
# UnexpectedSuccess: 0x8bb0a34b

# ###############
# ### Factory ###
# ###############
# Unauthorized: 0x82b42900
# InvalidContribution: 0x652122d9
# InvalidToken: 0xc1ab6dc1

# ######################
# ### ERC20Forwarder ###
# ######################
# BatchInputLengthMismatch: 0xba430d38
# ExpiredDeadline: 0xf87d9271
# InvalidSignature: 0x8baa579f
# InvalidERC20Bridge: 0x2aab8bd3
# RestrictedZeroAddress: 0xf0dd15fd

# ###################
# ### BondWrapper ###
# ###################
# AlreadyClosed: 0x9acb7e52
# BondMatured: 0x3f8e46bc
# BondNotMatured: 0x915eceb1
# InsufficientPrice: 0xd5481703

# ###############
# ### AssetId ###
# ###############
# InvalidTimestamp: 0xb7d09497

# ######################
# ### FixedPointMath ###
# ######################
# FixedPointMath_AddOverflow: 0x2d59cfbd
# FixedPointMath_SubOverflow: 0x35ba1440
# FixedPointMath_InvalidExponent: 0xdf92cc9d
# FixedPointMath_NegativeOrZeroInput: 0xac5f1b8e
# FixedPointMath_NegativeInput: 0x2c7949f5
