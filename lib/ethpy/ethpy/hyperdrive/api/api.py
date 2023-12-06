"""High-level interface for a Hyperdrive pool."""

# API file is a single class with lots of options
# pylint: disable=too-many-lines

from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING, cast

from ethpy import build_eth_config
from ethpy.base import initialize_web3_with_http_provider
from ethpy.hyperdrive.addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_uri
from ethpy.hyperdrive.state import PoolState
from ethpy.hyperdrive.transactions import (
    get_hyperdrive_checkpoint,
    get_hyperdrive_pool_config,
    get_hyperdrive_pool_info,
)
from fixedpointmath import FixedPoint
from hypertypes import IERC4626HyperdriveContract
from hypertypes.types import ERC20MintableContract, MockERC4626Contract
from web3.types import BlockData, BlockIdentifier, Timestamp

from ._block_getters import _get_block, _get_block_number, _get_block_time
from ._contract_calls import (
    _async_add_liquidity,
    _async_close_long,
    _async_close_short,
    _async_open_long,
    _async_open_short,
    _async_redeem_withdraw_shares,
    _async_remove_liquidity,
    _create_checkpoint,
    _get_eth_base_balances,
    _get_gov_fees_accrued,
    _get_hyperdrive_base_balance,
    _get_hyperdrive_eth_balance,
    _get_total_supply_withdrawal_shares,
    _get_variable_rate,
    _get_vault_shares,
    _set_variable_rate,
)
from ._mock_contract import (
    _calc_bonds_given_shares_and_rate,
    _calc_bonds_out_given_shares_in_down,
    _calc_checkpoint_id,
    _calc_effective_share_reserves,
    _calc_fees_out_given_bonds_in,
    _calc_fees_out_given_shares_in,
    _calc_fixed_rate,
    _calc_long_amount,
    _calc_max_buy,
    _calc_max_long,
    _calc_max_sell,
    _calc_max_short,
    _calc_position_duration_in_years,
    _calc_shares_in_given_bonds_out_down,
    _calc_shares_in_given_bonds_out_up,
    _calc_shares_out_given_bonds_in_down,
    _calc_short_deposit,
    _calc_spot_price,
)

# We expect to have many instance attributes & public methods since this is a large API.
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-arguments
# We only worry about protected access for anyone outside of this folder.
# pylint: disable=protected-access


if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber
    from ethpy import EthConfig
    from web3 import Web3
    from web3.types import Nonce

    from ..receipt_breakdown import ReceiptBreakdown


class HyperdriveInterface:
    """End-point API for interfacing with a deployed Hyperdrive pool."""

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        addresses: HyperdriveAddresses | None = None,
        web3: Web3 | None = None,
        read_retry_count: int | None = None,
        write_retry_count: int | None = None,
    ) -> None:
        """The HyperdriveInterface API.
        This is the primary endpoint for users to simulate as well as execute transactions on
        the Hyperdrive smart contracts.

        Arguments
        ---------
        eth_config: EthConfig, optional
            Configuration dataclass for the ethereum environment.
            If given, then it is constructed from environment variables.
        addresses: HyperdriveAddresses, optional
            This is a dataclass containing addresses for deployed hyperdrive and base token contracts.
            If given, then the `eth_config.artifacts_uri` variable is not used, and these Addresses are used instead.
            If not given, then addresses is constructed from the `addresses.json` file at `eth_config.artifacts_uri`.
        web3: Web3, optional
            web3 provider object, optional
            If given, a web3 object is constructed using the `eth_config.rpc_uri` as the http provider.
        """
        # Handle defaults for config and addresses.
        self.eth_config: EthConfig = build_eth_config() if eth_config is None else eth_config
        if addresses is None:
            addresses = fetch_hyperdrive_address_from_uri(os.path.join(self.eth_config.artifacts_uri, "addresses.json"))
        self.addresses: HyperdriveAddresses = addresses
        # Setup provider for communicating with the chain.
        if web3 is None:
            web3 = initialize_web3_with_http_provider(self.eth_config.rpc_uri, reset_provider=False)
        self.web3 = web3
        # Setup the ERC20 contract for minting base tokens.
        self.base_token_contract: ERC20MintableContract = ERC20MintableContract.factory(w3=self.web3)(
            web3.to_checksum_address(self.addresses.base_token)
        )
        # Setup Hyperdrive and Yield (variable rate) contracts.
        self.hyperdrive_contract: IERC4626HyperdriveContract = IERC4626HyperdriveContract.factory(w3=self.web3)(
            web3.to_checksum_address(self.addresses.mock_hyperdrive)
        )
        self.yield_address = self.hyperdrive_contract.functions.pool().call()
        self.yield_contract: MockERC4626Contract = MockERC4626Contract.factory(w3=self.web3)(
            address=web3.to_checksum_address(self.yield_address)
        )
        # Fill in the initial state cache.
        self._current_pool_state = self.get_hyperdrive_state()
        self.last_state_block_number = copy.copy(self._current_pool_state.block_number)
        self.pool_config = self._current_pool_state.pool_config
        # Set the retry count for contract calls using the interface when previewing/transacting
        # TODO these parameters are currently only used for trades against hyperdrive
        # and uses defaults for other smart_contract_read functions, e.g., get_pool_info.
        self.read_retry_count = read_retry_count
        self.write_retry_count = write_retry_count

    @property
    def current_pool_state(self) -> PoolState:
        """The current state of the pool.

        Each time this is accessed we use an RPC to check that the pool state is synced with the current block.
        """
        _ = self._ensure_current_state()
        return self._current_pool_state

    def _ensure_current_state(self) -> bool:
        """Update the cached pool info and latest checkpoint if needed.

        Returns
        -------
        bool
            True if the state was updated.
        """
        current_block = self.get_current_block()
        current_block_number = self.get_block_number(current_block)
        if current_block_number > self.last_state_block_number:
            self._current_pool_state = self.get_hyperdrive_state(current_block)
            self.last_state_block_number = current_block_number
            return True
        return False

    def get_current_block(self) -> BlockData:
        """Use an RPC to get the current block.

        Returns
        -------
        BlockData
            A web3py dataclass containing information about the latest mined block.
        """
        return self.get_block("latest")

    def get_block(self, block_identifier: BlockIdentifier) -> BlockData:
        """Use an RPC to get the block for the provided identifier.

        Delegates to eth_getBlockByNumber if block_identifier is an integer or
        one of the predefined block parameters 'latest', 'earliest', 'pending', 'safe', 'finalized'.
        Otherwise delegates to eth_getBlockByHash.
        Throws BlockNotFound error if the block is not found.

        Arguments
        ---------
        block_identifier: BlockIdentifier
            Any one of the web3py types: [BlockParams, BlockNumber, Hash32, HexStr, HexBytes, int].

        Returns
        -------
        BlockData
            A web3py dataclass containing block information.
        """
        return _get_block(self, block_identifier)

    def get_block_number(self, block: BlockData) -> BlockNumber:
        """Use an RPC to get the number for the provided block.

        Arguments
        ---------
        block: BlockData
            A web3py dataclass for storing block information.

        Returns
        -------
        BlockNumber
            The number for the corresponding block.
        """
        return _get_block_number(block)

    def get_block_timestamp(self, block: BlockData) -> Timestamp:
        """Use an RPC to get the time for the provided block.

        Arguments
        ---------
        block: BlockData
            A web3py dataclass for storing block information.

        Returns
        -------
        Timestamp
            The integer timestamp, in seconds, for the corresponding block.
        """
        return _get_block_time(block)

    def get_hyperdrive_state(self, block: BlockData | None = None):
        """Use RPCs and contract calls to get the Hyperdrive pool and block state, given a block identifier.

        Arguments
        ---------
        block: BlockData, optional
            A web3py dataclass for storing block information.
            Defaults to the latest block.

        Returns
        -------
        PoolState
            A dataclass containing PoolInfo, PoolConfig, Checkpoint, and Block
            information that is synced to a given block number.
        """
        if block is None:
            block_identifier = cast(BlockIdentifier, "latest")
            block = self.get_block(block_identifier)
        block_number = self.get_block_number(block)
        pool_config = get_hyperdrive_pool_config(self.hyperdrive_contract)
        pool_info = get_hyperdrive_pool_info(self.hyperdrive_contract, block_number)
        checkpoint = get_hyperdrive_checkpoint(
            self.hyperdrive_contract,
            self.calc_checkpoint_id(pool_config.checkpoint_duration, self.get_block_timestamp(block)),
        )
        variable_rate = self.get_variable_rate(block_number)
        vault_shares = self.get_vault_shares(block_number)
        total_supply_withdrawal_shares = self.get_total_supply_withdrawal_shares(block_number)
        hyperdrive_base_balance = self.get_hyperdrive_base_balance(block_number)
        hyperdrive_eth_balance = self.get_hyperdrive_eth_balance()
        gov_fees_accrued = self.get_gov_fees_accrued(block_number)
        return PoolState(
            block,
            pool_config,
            pool_info,
            checkpoint,
            variable_rate,
            vault_shares,
            total_supply_withdrawal_shares,
            hyperdrive_base_balance,
            hyperdrive_eth_balance,
            gov_fees_accrued,
        )

    def get_total_supply_withdrawal_shares(self, block_number: BlockNumber | None) -> FixedPoint:
        """Use an RPC to get the total supply of withdrawal shares in the pool at the given block.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            If not given, the latest block number is used.

        Returns
        -------
        FixedPoint
            The quantity of withdrawal shares available in the Hyperdrive pool.
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        return _get_total_supply_withdrawal_shares(self.hyperdrive_contract, block_number)

    def get_vault_shares(self, block_number: BlockNumber | None) -> FixedPoint:
        """Use an RPC to get the balance of shares that the Hyperdrive pool has in the underlying yield source.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The quantity of vault shares for the yield source at the provided block.
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        return _get_vault_shares(self.yield_contract, self.hyperdrive_contract, block_number)

    def get_variable_rate(self, block_number: BlockNumber | None) -> FixedPoint:
        """Use an RPC to get the yield source variable rate.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The variable rate for the yield source at the provided block.
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        return _get_variable_rate(self.yield_contract, block_number)

    def get_eth_base_balances(self, agent: LocalAccount) -> tuple[FixedPoint, FixedPoint]:
        """Use an RPC to get the agent's balance on the Base & Hyperdrive contracts.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.

        Returns
        -------
        tuple[FixedPoint]
            A tuple containing the [agent_eth_balance, agent_base_balance].
        """
        return _get_eth_base_balances(self, agent)

    def get_hyperdrive_eth_balance(self) -> FixedPoint:
        """Get the current Hyperdrive eth balance from an RPC.

        Returns
        -------
        FixedPoint
            The eth on the chain.
        """
        return _get_hyperdrive_eth_balance(self.web3, self.hyperdrive_contract.address)

    def get_hyperdrive_base_balance(self, block_number: BlockNumber | None) -> FixedPoint:
        """Get the current Hyperdrive balance in the base contract.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The result of base_token_contract.balanceOf(hypedrive_address).
        """
        return _get_hyperdrive_base_balance(self.base_token_contract, self.hyperdrive_contract, block_number)

    def get_gov_fees_accrued(self, block_number: BlockNumber | None = None) -> FixedPoint:
        """Get the current amount of Uncollected Governance Fees in the Hyperdrive contract.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The result of hyperdrive_contract.functions.getUncollectedGovernanceFees
        """
        return _get_gov_fees_accrued(self.hyperdrive_contract, block_number)

    def create_checkpoint(
        self, sender: LocalAccount, block_number: BlockNumber | None = None, checkpoint_time: int | None = None
    ) -> ReceiptBreakdown:
        """Create a Hyperdrive checkpoint.

        Arguments
        ---------
        sender: LocalAccount
            The sender account that is executing and signing the trade transaction.
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.
        checkpoint_time: int, optional
            The checkpoint time to use. Defaults to the corresponding checkpoint for the provided block_number

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the output event of the contract call.
        """
        return _create_checkpoint(self, sender, block_number, checkpoint_time)

    def set_variable_rate(self, sender: LocalAccount, new_rate: FixedPoint) -> None:
        """Set the variable rate for the yield source.

        Arguments
        ---------
        sender: LocalAccount
            The sender account that is executing and signing the trade transaction.
        new_rate: FixedPoint
            The new variable rate for the yield source.
        """
        _set_variable_rate(self, sender, new_rate)

    async def async_open_long(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to open a long position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An optional explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_open_long(self, agent, trade_amount, slippage_tolerance, nonce)

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_close_long(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a long position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        maturity_time: int
            The token maturity time in seconds.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An optional explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_close_long(self, agent, trade_amount, maturity_time, slippage_tolerance, nonce)

    async def async_open_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to open a short position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_open_short(self, agent, trade_amount, slippage_tolerance, nonce)

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_close_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a short position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        maturity_time: int
            The token maturity time in seconds.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_close_short(self, agent, trade_amount, maturity_time, slippage_tolerance, nonce)

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_add_liquidity(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        min_apr: FixedPoint,
        max_apr: FixedPoint,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to add liquidity to the Hyperdrive pool.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        min_apr: FixedPoint
            The minimum allowable APR after liquidity is added.
        max_apr: FixedPoint
            The maximum allowable APR after liquidity is added.
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed.
        """
        return await _async_add_liquidity(self, agent, trade_amount, min_apr, max_apr, nonce)

    async def async_remove_liquidity(
        self, agent: LocalAccount, trade_amount: FixedPoint, nonce: Nonce | None = None
    ) -> ReceiptBreakdown:
        """Contract call to remove liquidity from the Hyperdrive pool.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed.
        """
        return await _async_remove_liquidity(self, agent, trade_amount, nonce)

    async def async_redeem_withdraw_shares(
        self, agent: LocalAccount, trade_amount: FixedPoint, nonce: Nonce | None = None
    ) -> ReceiptBreakdown:
        """Contract call to redeem withdraw shares from Hyperdrive pool.
        This should be done after closing liquidity.

        .. note::
            This is not guaranteed to redeem all shares. The pool will try to redeem as
            many as possible, up to the withdrawPool.readyToRedeem limit, without reverting.
            This will revert if the min_output is too high or the user is trying to withdraw
            more shares than they have.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        nonce: Nonce | None, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed.
        """
        return await _async_redeem_withdraw_shares(self, agent, trade_amount, nonce)

    def calc_position_duration_in_years(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Returns the pool config position duration as a fraction of a year.

        This "annualized" time value is used in some calculations, such as the Fixed APR.
        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The annualized position duration
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_position_duration_in_years(pool_state)

    def calc_checkpoint_id(
        self, checkpoint_duration: int | None = None, block_timestamp: Timestamp | None = None
    ) -> Timestamp:
        """Calculate the Checkpoint ID for a given timestamp.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        checkpoint_duration: int, optional
            The time, in seconds, between checkpoints.
            Defaults to the current pool's checkpoint duration.
        block_timestamp: Timestamp, optional
            A timestamp for any block. Use the latest block to get the current checkpoint id,
            or a specific timestamp of a transaction's block if getting the checkpoint id for that transaction.
            Defaults to the current block timestamp.

        Returns
        -------
        int
            The checkpoint id, which can be used as an argument for the Hyperdrive getCheckpoint function.
        """
        if checkpoint_duration is None:
            checkpoint_duration = self.current_pool_state.pool_config.checkpoint_duration
        if block_timestamp is None:
            block_timestamp = self.current_pool_state.block_time
        return _calc_checkpoint_id(checkpoint_duration, block_timestamp)

    def calc_fixed_rate(self, pool_state: PoolState | None = None) -> FixedPoint:
        r"""Calculate the fixed rate for a given pool state.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. The simulation follows the formula:

        .. math::
            r = ((1 / p) - 1) / t = (1 - p) / (p * t)

        Arguments
        ---------
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The fixed rate apr for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_fixed_rate(pool_state)

    def calc_spot_price(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the spot price for a given Hyperdrive pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The spot price for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_spot_price(pool_state)

    def calc_effective_share_reserves(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the adjusted share reserves for a given Hyperdrive pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The effective (aka zeta-adjusted) share reserves.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_effective_share_reserves(pool_state)

    def calc_open_long(self, base_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the long amount that will be opened for a given base amount after fees.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        base_amount: FixedPoint
            The amount to spend, in base.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of bonds purchased.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_long_amount(pool_state, base_amount)

    def calc_open_short(self, bond_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the amount of base the trader will need to deposit for a short of a given size, after fees.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount to of bonds to short.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of base required to short the bonds (aka the "max loss").
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_short_deposit(
            pool_state, bond_amount, _calc_spot_price(pool_state), pool_state.pool_info.share_price
        )

    def calc_bonds_out_given_shares_in_down(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of bonds a user will receive from the pool by
        providing a specified amount of shares. We underestimate the amount of
        bonds. The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of shares going into the pool.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of bonds out.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_bonds_out_given_shares_in_down(pool_state, amount_in)

    def calc_shares_in_given_bonds_out_up(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of shares a user must provide the pool to receive
        a specified amount of bonds. We overestimate the amount of shares in.
        The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds to target.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares in to reach the target.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_shares_in_given_bonds_out_up(pool_state, amount_in)

    def calc_shares_in_given_bonds_out_down(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of shares a user must provide the pool to receive
        a specified amount of bonds. We underestimate the amount of shares in.
        The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds to target.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares in to reach the target.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_shares_in_given_bonds_out_down(pool_state, amount_in)

    def calc_shares_out_given_bonds_in_down(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of shares a user will receive from the pool by
        providing a specified amount of bonds. We underestimate the amount of
        shares out. The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds in.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares out.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_shares_out_given_bonds_in_down(pool_state, amount_in)

    def calc_max_buy(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculates the maximum amount of bonds that can be purchased with the
        specified reserves. We round so that the max buy amount is
        underestimated.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum buy amount
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_max_buy(pool_state)

    def calc_max_sell(self, minimum_share_reserves: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculates the maximum amount of bonds that can be sold with the
        specified reserves. We round so that the max sell amount is
        underestimated.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        minimum_share_reserves: FixedPoint
            The minimum share reserves to target
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum sell amount
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_max_sell(pool_state, minimum_share_reserves)

    def calc_fees_out_given_bonds_in(
        self, bonds_in: FixedPoint, maturity_time: int | None = None, pool_state: PoolState | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        r"""Calculates the fees that would be deducted for an amount of bonds entering the pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. It implements the formula:

        .. math::
            \begin{align*}
                &\text{curve_fee} = \frac{(1 - p) * \phi_{\text{curve}} * d_y * t}{c}
                &\text{gov_fee} = \text{curve_fee} * \phi_{\text{gov}}
                &\text{flat_fee} = \frac{d_y * (1 - t) * \phi_{\text{flat}}}{c}
            \end{align*}

        Arguments
        ---------
        bonds_in: FixedPoint
            The amount of bonds being added to the pool.
        maturity_time: int, optional
            The maturity timestamp of the open position, in epoch seconds.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint]
            curve_fee: FixedPoint
                Curve fee, in shares.
            flat_fee: FixedPoint
                Flat fee, in shares.
            gov_fee: FixedPoint
                Governance fee, in shares.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_fees_out_given_bonds_in(pool_state, bonds_in, maturity_time)

    def calc_fees_out_given_shares_in(
        self, shares_in: FixedPoint, maturity_time: int | None = None, pool_state: PoolState | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        r"""Calculates the fees that go to the LPs and governance.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. It implements the formula:

        .. math::
            \begin{align*}
                &\text{curve_fee} = ((1 / p) - 1) * \phi_{\text{curve}} * c * dz
                &\text{gov_fee} = \text{shares} * \phi_{\text{gov}}
                &\text{flat_fee} = \frac{d_y * (1 - t) * \phi_{\text{flat}}}{c}
            \end{align*}

        Arguments
        ---------
        shares_in: FixedPoint
            The amount of shares being added to the pool.
        maturity_time: int, optional
            The maturity timestamp of the open position, in epoch seconds.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint]
            curve_fee: FixedPoint
                Curve fee, in shares.
            flat_fee: FixedPoint
                Flat fee, in shares.
            gov_fee: FixedPoint
                Governance fee, in shares.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_fees_out_given_shares_in(pool_state, shares_in, maturity_time)

    def calc_bonds_given_shares_and_rate(
        self, target_rate: FixedPoint, target_shares: FixedPoint | None = None, pool_state: PoolState | None = None
    ) -> FixedPoint:
        r"""Returns the bond reserves for the market share reserves
        and a given fixed rate.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. The calculation is based on the formula:

        .. math::
            \mu * (z - \zeta) * (1 + \text{apr} * t)^{1 / \tau}

        .. todo::
            This function name matches the Rust implementation, but is not preferred because
            "given_shares_and_rate" is in the wrong order (should be rate_and_shares) according to arguments
            and really "given_*" could be removed because it can be inferred from arguments.
            Need to fix it from the bottom up.

        Arguments
        ---------
        target_rate: FixedPoint
            The target apr for which to calculate the bond reserves given the pools current share reserves.
        target_shares: FixedPoint, optional
            The target share reserves for the pool
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The output bonds.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_bonds_given_shares_and_rate(pool_state, target_rate, target_shares)

    def calc_max_long(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable long for the given Hyperdrive pool and agent budget.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum long, in units of base.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_max_long(pool_state, budget)

    def calc_max_short(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable short for the given Hyperdrive pool and agent budget.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state: PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum short, in units of bonds.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_max_short(pool_state, budget)
