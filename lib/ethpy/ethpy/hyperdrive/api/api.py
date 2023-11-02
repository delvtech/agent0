"""High-level interface for the Hyperdrive market."""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from ethpy import build_eth_config
from ethpy.base import initialize_web3_with_http_provider, load_all_abis, smart_contract_read
from ethpy.hyperdrive.addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_uri
from ethpy.hyperdrive.transactions import (
    convert_hyperdrive_checkpoint_types,
    convert_hyperdrive_pool_config_types,
    convert_hyperdrive_pool_info_types,
    get_hyperdrive_checkpoint,
    get_hyperdrive_pool_config,
    get_hyperdrive_pool_info,
)
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
    _get_eth_base_balances,
    _get_variable_rate,
    _get_vault_shares,
)
from ._mock_contract import (
    _calc_bonds_given_shares_and_rate,
    _calc_checkpoint_id,
    _calc_effective_share_reserves,
    _calc_fees_out_given_bonds_in,
    _calc_fees_out_given_shares_in,
    _calc_fixed_rate,
    _calc_in_for_out,
    _calc_long_amount,
    _calc_max_long,
    _calc_max_short,
    _calc_out_for_in,
    _calc_position_duration_in_years,
    _calc_short_deposit,
    _calc_spot_price,
)

# We expect to have many instance attributes & public methods since this is a large API.
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-arguments
# We only worry about protected access for anyone outside of this folder
# pylint: disable=protected-access


if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber
    from ethpy import EthConfig
    from fixedpointmath import FixedPoint
    from web3 import Web3
    from web3.contract.contract import Contract
    from web3.types import Nonce

    from ..receipt_breakdown import ReceiptBreakdown


@dataclass
class PoolState:
    r"""A collection of stateful variables for a deployed Hyperdrive and Yield contracts."""
    hyperdrive_contract: Contract
    yield_contract: Contract
    block: BlockData

    def __post_init__(self):
        self.block_number = _get_block_number(self.block)
        self.block_time = _get_block_time(self.block)
        self.contract_pool_config = get_hyperdrive_pool_config(self.hyperdrive_contract)
        self.pool_config = convert_hyperdrive_pool_config_types(self.contract_pool_config)
        self.contract_pool_info = get_hyperdrive_pool_info(self.hyperdrive_contract, self.block_number)
        # TODO: Get the rest of the extra process pool info values as extra attributes
        # These are constructed a few times in chainsync; would be nice to clean that up
        # by computing here
        self.pool_info = convert_hyperdrive_pool_info_types(self.contract_pool_info)
        self.contract_checkpoint = get_hyperdrive_checkpoint(
            self.hyperdrive_contract, _calc_checkpoint_id(self, self.block_time)
        )
        self.variable_rate = _get_variable_rate(self.yield_contract, self.block_number)
        self.vault_shares = _get_vault_shares(self.yield_contract, self.hyperdrive_contract, self.block_number)
        self.checkpoint = convert_hyperdrive_checkpoint_types(self.contract_checkpoint)


class HyperdriveInterface:
    """End-point api for interfacing with Hyperdrive."""

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        addresses: HyperdriveAddresses | None = None,
        web3: Web3 | None = None,
    ) -> None:
        """The HyperdriveInterface API.

        HyperdriveInterface requires an EthConfig to initialize.
        If the user does not provide one, then it is constructed from environment variables.
        The user can optionally include an `artifacts` HyperdriveAddresses object.
        In this case, the `eth_config.artifacts_uri` variable is not used, and these Addresses are used instead.
        """
        # Handle defaults for config and addresses
        self.eth_config: EthConfig = build_eth_config() if eth_config is None else eth_config
        if addresses is None:
            addresses = fetch_hyperdrive_address_from_uri(os.path.join(self.eth_config.artifacts_uri, "addresses.json"))
        self.addresses: HyperdriveAddresses = addresses
        # Setup provider for communicating with the chain
        if web3 is None:
            web3 = initialize_web3_with_http_provider(self.eth_config.rpc_uri, reset_provider=False)
        self.web3 = web3
        abis = load_all_abis(self.eth_config.abi_dir)
        # set up the ERC20 contract for minting base tokens
        self.base_token_contract: Contract = web3.eth.contract(
            abi=abis["ERC20Mintable"], address=web3.to_checksum_address(self.addresses.base_token)
        )
        # set up hyperdrive contract
        self.hyperdrive_contract: Contract = web3.eth.contract(
            abi=abis["IHyperdrive"], address=web3.to_checksum_address(self.addresses.mock_hyperdrive)
        )
        # get yield (variable rate) pool contract
        # TODO: In the future we want to switch to a single IERC4626Hyperdrive ABI
        data_provider_contract: Contract = web3.eth.contract(
            abi=abis["ERC4626DataProvider"], address=web3.to_checksum_address(self.addresses.mock_hyperdrive)
        )
        self.yield_address = smart_contract_read(data_provider_contract, "pool")["value"]
        self.yield_contract: Contract = web3.eth.contract(
            abi=abis["MockERC4626"], address=web3.to_checksum_address(self.yield_address)
        )
        # fill in initial cache
        self.current_pool_state = self.get_hyperdrive_state()
        self.last_state_block_number = copy.copy(self.current_pool_state.block_number)

    @property
    def current_block(self) -> BlockData:
        """The current block."""
        return self.block("latest")

    def block(self, block_identifier: BlockIdentifier) -> BlockData:
        """Return the block for the provided identifier.

        Delegates to eth_getBlockByNumber if block_identifier is an integer or
        one of the predefined block parameters 'latest', 'earliest', 'pending', 'safe', 'finalized'.
        Otherwise delegates to eth_getBlockByHash.
        Throws BlockNotFound error if the block is not found.

        Arguments
        ---------
        block_identifier : BlockIdentifier
            Any one of the web3py types: [BlockParams, BlockNumber, Hash32, HexStr, HexBytes, int].
        """
        return _get_block(self, block_identifier)

    def block_number(self, block: BlockData) -> BlockNumber:
        """Return the number for the provided block.

        Arguments
        ---------
        block : BlockData
            A web3py dataclass for storing block information.

        Returns
        -------
        BlockNumber
            The number for the corresponding block
        """
        return _get_block_number(block)

    def block_timestamp(self, block: BlockData) -> Timestamp:
        """Return the time for the provided block.

        Arguments
        ---------
        block : BlockData
            A web3py dataclass for storing block information.

        Returns
        -------
        Timestamp
            The integer timestamp, in seconds, for the corresponding block.
        """
        return _get_block_time(block)

    def _ensure_current_state(self) -> None:
        """Update the cached pool info and latest checkpoint if needed."""
        if self.current_pool_state.block_number > self.last_state_block_number:
            self.current_pool_state = self.get_hyperdrive_state()
            self.last_state_block_number = copy.copy(self.current_pool_state.block_number)

    def get_hyperdrive_state(self, block: BlockData | None = None):
        """Get the hyperdrive pool and block state, given a block identifier.

        Arguments
        ---------
        block : BlockData, optional
            A web3py dataclass for storing block information.

        """
        if block is None:
            block_identifier = cast(BlockIdentifier, "latest")
            block = self.block(block_identifier)
        return PoolState(self.hyperdrive_contract, self.yield_contract, block)

    def get_eth_base_balances(self, agent: LocalAccount) -> tuple[FixedPoint, FixedPoint]:
        """Get the agent's balance on the Hyperdrive & base contracts.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.

        Returns
        -------
        tuple[FixedPoint]
            A tuple containing the [agent_eth_balance, agent_base_balance]
        """
        return _get_eth_base_balances(self, agent)

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
        slippage_tolerance: FixedPoint | None
            Amount of slippage allowed from the trade.
            If None, then execute the trade regardless of the slippage.
            If not None, then the trade will not execute unless the slippage is below this value.
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        return await _async_open_long(self, agent, trade_amount, slippage_tolerance, nonce)

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
        slippage_tolerance: FixedPoint | None
            Amount of slippage allowed from the trade.
            If None, then execute the trade regardless of the slippage.
            If not None, then the trade will not execute unless the slippage is below this value.
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
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
        slippage_tolerance: FixedPoint | None
            Amount of slippage allowed from the trade.
            If None, then execute the trade regardless of the slippage.
            If not None, then the trade will not execute unless the slippage is below this value.
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        return await _async_open_short(self, agent, trade_amount, slippage_tolerance, nonce)

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
        slippage_tolerance: FixedPoint | None
            Amount of slippage allowed from the trade.
            If None, then execute the trade regardless of the slippage.
            If not None, then the trade will not execute unless the slippage is below this value.
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        return await _async_close_short(self, agent, trade_amount, maturity_time, slippage_tolerance, nonce)

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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
        """
        return await _async_remove_liquidity(self, agent, trade_amount, nonce)

    async def async_redeem_withdraw_shares(
        self, agent: LocalAccount, trade_amount: FixedPoint, nonce: Nonce | None = None
    ) -> ReceiptBreakdown:
        """Contract call to redeem withdraw shares from Hyperdrive pool.

        This should be done after closing liquidity.

        .. note::
            This is not guaranteed to redeem all shares.  The pool will try to redeem as
            many as possible, up to the withdrawPool.readyToRedeem limit, without reverting.
            Only a min_output that is too high will cause a revert here, or trying to
            withdraw more shares than the user has obviously.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        min_output: FixedPoint
            The minimum output amount
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
        """
        return await _async_redeem_withdraw_shares(self, agent, trade_amount, nonce)

    def calc_position_duration_in_years(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Returns the pool config position duration as a fraction of a year.

        This "annualized" time value is used in some calculations, such as the Fixed APR.

        Arguments
        ---------
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The annualized position duration
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_position_duration_in_years(self.current_pool_state)

    def calc_checkpoint_id(self, block_timestamp: Timestamp, pool_state: PoolState | None = None) -> Timestamp:
        """Calculate the Checkpoint ID for a given timestamp.

        Arguments
        ---------
        block_timestamp : Timestamp
            A timestamp for any block. Use the latest block to get the current checkpoint id,
            or a specific timestamp of a transaction's block if getting the checkpoint id for that transaction.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        int
            The checkpoint id, which can be used as an argument for the Hyperdrive getCheckpoint function.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_checkpoint_id(pool_state, block_timestamp)

    def calc_fixed_rate(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the fixed rate for a given pool state.

        Follows the formula:

        .. math::
            r = ((1 / p) - 1) / t = (1 - p) / (p * t)

        Arguments
        ---------
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_fixed_rate(pool_state)

    def calc_spot_price(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the spot price for a given Hyperdrive pool.

        Arguments
        ---------
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The current spot price.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_spot_price(pool_state)

    def calc_effective_share_reserves(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the adjusted share reserves for a given Hyperdrive pool.

        Arguments
        ---------
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The effective (aka zeta-adjusted) share reserves.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_effective_share_reserves(pool_state)

    def calc_open_long(self, base_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the long amount that will be opened for a given base amount after fees.

        Arguments
        ---------
        base_amount : FixedPoint
            The amount to spend, in base.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of bonds purchased.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_long_amount(pool_state, base_amount)

    def calc_open_short(self, short_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the amount of base the trader will need to deposit for a short of a given size.

        Arguments
        ---------
        short_amount : FixedPoint
            The amount to of bonds to short.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        short_amount : FixedPoint
            The amount of base required to short the bonds (aka the "max loss").
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_short_deposit(
            pool_state, short_amount, _calc_spot_price(pool_state), pool_state.pool_info.share_price
        )

    def calc_out_for_in(
        self, amount_in: FixedPoint, shares_in: bool, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the amount of an asset for a given amount in of the other.

        Arguments
        ---------
        amount_in : FixedPoint
            The amount going into the pool.
        shares_in : bool
            True if the asset in is shares; False if it is bonds.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount out.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_out_for_in(pool_state, amount_in, shares_in)

    def calc_in_for_out(
        self, amount_out: FixedPoint, shares_out: bool, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the amount of an asset for a given amount out of the other.

        Arguments
        ---------
        amount_out : FixedPoint
            The amount coming out of the pool.
        shares_out : bool
            True if the asset out is shares, False if it is bonds.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount in.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_in_for_out(pool_state, amount_out, shares_out)

    def calc_fees_out_given_bonds_in(
        self, bonds_in: FixedPoint, maturity_time: int | None = None, pool_state: PoolState | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        """Calculates the fees that go to the LPs and governance.

        Implements the formula:
            curve_fee = ((1 - p) * phi_curve * d_y * t)/c
            gov_fee = curve_fee * phi_gov
            flat_fee = (d_y * (1 - t) * phi_flat) / c

        Arguments
        ---------
        bonds_in : FixedPoint
            The amount of bonds being added to the pool.
        maturity_time : int, optional
            The maturity timestamp of the open position, in epoch seconds.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint] consisting of:
            curve_fee : FixedPoint
                Curve fee, in shares.
            flat_fee : FixedPoint
                Flat fee, in shares.
            gov_fee : FixedPoint
                Governance fee, in shares.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_fees_out_given_bonds_in(pool_state, bonds_in, maturity_time)

    def calc_fees_out_given_shares_in(
        self, shares_in: FixedPoint, maturity_time: int | None = None, pool_state: PoolState | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        """Calculates the fees that go to the LPs and governance.

        Implements the formula:
            curve_fee = ((1 / p) - 1) * phi_curve * c * dz
            gov_fee = shares * phi_gov
            flat_fee = (d_y * (1 - t) * phi_flat) / c

        Arguments
        ---------
        shares_in : FixedPoint
            The amount of shares being added to the pool.
        maturity_time : int, optional
            The maturity timestamp of the open position, in epoch seconds.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint] consisting of:
            curve_fee : FixedPoint
                Curve fee, in shares.
            flat_fee : FixedPoint
                Flat fee, in shares.
            gov_fee : FixedPoint
                Governance fee, in shares.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_fees_out_given_shares_in(pool_state, shares_in, maturity_time)

    def calc_bonds_given_shares_and_rate(
        self, target_rate: FixedPoint, target_shares: FixedPoint | None = None, pool_state: PoolState | None = None
    ) -> FixedPoint:
        r"""Returns the bond reserves for the market share reserves
        and a given fixed rate.


        The calculation is based on the formula:

        .. math::
            mu * (z - zeta) * (1 + apr * t) ** (1 / tau)

        Arguments
        ---------
        target_rate : FixedPoint
            The target apr for which to calculate the bond reserves given the pools current share reserves.
        target_shares : FixedPoint, optional
            The target share reserves for the pool
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        .. todo::
            This function name matches the Rust implementation, but is not preferred because
            "given_shares_and_rate" is in the wrong order (should be rate_and_shares) according to arguments
            and really "given_*" could be removed because it can be inferred from arguments.
            Need to fix it from the bottom up.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_bonds_given_shares_and_rate(pool_state, target_rate, target_shares)

    def calc_max_long(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable long for the given Hyperdrive pool and agent budget.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum long, in units of base.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_max_long(pool_state, budget)

    def calc_max_short(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable short for the given Hyperdrive pool and agent budget.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state : PoolState, optional
            The current state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum short, in units of base.
        """
        if pool_state is None:
            self._ensure_current_state()
            pool_state = self.current_pool_state
        return _calc_max_short(pool_state, budget)
