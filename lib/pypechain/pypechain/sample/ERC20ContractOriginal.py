# pylint: disable=C0103
"""Working file to check outputs of run_pypechain.py against.  TODOs kept track of in here as well
as in the jinja template"""
from __future__ import annotations

from typing import Any, NamedTuple, cast

from eth_typing import ChecksumAddress
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound
from web3.types import BlockIdentifier, CallOverride, TxParams

# TODO: break out function classes to their own files?


class AllowanceOutput(NamedTuple):
    """Output for the allowance method."""

    arg1: str


class AllowanceContractFunction(ContractFunction):
    """ContractFunction for the allowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, owner: str, spender: str) -> "AllowanceContractFunction":
        super().__call__(owner, spender)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> AllowanceOutput:
        """
        Execute a contract function call using the `eth_call` interface.

        See web3.py ContractFunction's call method for more info.

        Arguments
        ---------
        transaction : TxParams | None
            Dictionary of transaction info for web3 interface.
        block_identifier : BlockIdentifier
            Hash or string used to identify a block, see BlockIdentifier for more info.
        state_override : CallOverride
            A dictionary keyed by contract address of eth_call overrides.
        ccip_read_enabled : bool

        Returns
        -------
            Returns the output of the contract.
        """

        result = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        return result


class ApproveContractFunction(ContractFunction):
    """ContractFunction for the Approve method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: str, amount: str) -> "ApproveContractFunction":
        super().__call__(spender, amount)
        return self


class ERC20ContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC20 contract."""

    allowance: AllowanceContractFunction
    approve: ContractFunction


# TODO: Add Events.  These will have names like class ERC20TransferSingleEvent
# class ERC20ContractEvents(ContractEvents):


class ERC20Contract(Contract):
    """A web3.py Contract class for the ERC20 contract."""

    def __init__(self, address: ChecksumAddress | None = None, abi=Any) -> None:
        self.abi = abi
        # TODO: make this better, shouldn't initialize to the zero address, but the Contract's init
        # function requires an address.
        self.address = address if address else cast(ChecksumAddress, "0x0000000000000000000000000000000000000000")

        try:
            # Initialize parent Contract class
            super().__init__(address=address)

            # TODO: Additional initialization, if any
            # self.functions = super().functions

            # TODO: map types like 'address' to Address
            # TODO: map inputs to functions.functionName.args

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC20ContractFunctions
