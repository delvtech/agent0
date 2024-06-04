"""Tests interactive hyperdrive end to end."""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Type

import numpy as np
import pandas as pd
import pytest
from fixedpointmath import FixedPoint, isclose
from pandas import Series

from agent0.chainsync.dashboard import build_pool_dashboard, build_wallet_dashboard
from agent0.core.base import Trade
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy, PolicyZoo
from agent0.core.test_utils import CycleTradesPolicy
from agent0.ethpy.hyperdrive import AssetIdPrefix, HyperdriveReadInterface, encode_asset_id

from .local_chain import LocalChain
from .local_hyperdrive import LocalHyperdrive
from .local_hyperdrive_agent import LocalHyperdriveAgent

YEAR_IN_SECONDS = 31_536_000

# needed to pass in fixtures
# pylint: disable=redefined-outer-name
# ruff: noqa: PLR2004 (comparison against magic values (literals like numbers))
# allow non-lazy logging
# pylint: disable=logging-fstring-interpolation

# Long test file
# pylint: disable=too-many-lines

# pylint: disable=protected-access


def _ensure_db_wallet_matches_agent_wallet_and_chain(in_hyperdrive: LocalHyperdrive, agent: LocalHyperdriveAgent):
    # pylint: disable=too-many-locals

    # NOTE this function is assuming only one agent is making trades
    interface = in_hyperdrive.interface

    # Test against pool positions
    positions_df = in_hyperdrive.get_positions(coerce_float=False)
    # Filter for wallet
    # We reset indices here to match indices with agent positions
    positions_df = positions_df[positions_df["wallet_address"] == agent.address].reset_index(drop=True)

    # Check against agent positions
    agent_positions = agent.get_positions(coerce_float=False)
    assert positions_df.equals(agent_positions)

    agent_wallet = agent.get_wallet()

    # Check base
    base_from_chain = interface.base_token_contract.functions.balanceOf(agent.address).call()
    assert agent_wallet.balance.amount == FixedPoint(scaled_value=base_from_chain)

    # Check lp
    lp_wallet_df = positions_df[positions_df["token_type"] == "LP"]
    if len(lp_wallet_df) == 0:
        check_value = FixedPoint(0)
    elif len(lp_wallet_df) == 1:
        check_value = FixedPoint(lp_wallet_df.iloc[0]["token_balance"])
    else:
        assert False
    assert check_value == agent_wallet.lp_tokens
    asset_id = encode_asset_id(AssetIdPrefix.LP, 0)
    lp_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, agent.address).call()
    assert check_value == FixedPoint(scaled_value=lp_from_chain)

    # Check withdrawal_shares
    withdrawal_wallet_df = positions_df[positions_df["token_type"] == "WITHDRAWAL_SHARE"]
    if len(withdrawal_wallet_df) == 0:
        check_value = FixedPoint(0)
    elif len(withdrawal_wallet_df) == 1:
        check_value = FixedPoint(withdrawal_wallet_df.iloc[0]["token_balance"])
    else:
        assert False
    assert check_value == agent_wallet.withdraw_shares
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    withdrawal_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, agent.address).call()
    assert check_value == FixedPoint(scaled_value=withdrawal_from_chain)

    # Check longs
    # Longs still show up in positions even if they're 0, since they also keep track of values
    long_wallet_df = positions_df[positions_df["token_type"] == "LONG"]
    assert len(long_wallet_df) == len(agent_wallet.longs)
    for _, long_df in long_wallet_df.iterrows():
        maturity_time = int(long_df["maturity_time"])
        assert maturity_time in agent_wallet.longs
        assert agent_wallet.longs[maturity_time].balance == long_df["token_balance"]
        asset_id = encode_asset_id(AssetIdPrefix.LONG, maturity_time)
        long_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, agent.address).call()
        assert FixedPoint(scaled_value=long_from_chain) == FixedPoint(long_df["token_balance"])

    # Check shorts
    short_wallet_df = positions_df[positions_df["token_type"] == "SHORT"]
    assert len(short_wallet_df) == len(agent_wallet.shorts)
    for _, short_df in short_wallet_df.iterrows():
        maturity_time = int(short_df["maturity_time"])
        assert maturity_time in agent_wallet.shorts
        assert agent_wallet.shorts[maturity_time].balance == short_df["token_balance"]
        asset_id = encode_asset_id(AssetIdPrefix.SHORT, maturity_time)
        short_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, agent.address).call()
        assert FixedPoint(scaled_value=short_from_chain) == FixedPoint(short_df["token_balance"])


# Lots of things to test
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# ruff: noqa: PLR0915 (too many statements)
@pytest.mark.anvil
def test_funding_and_trades(fast_chain_fixture: LocalChain):
    """Deploy 2 pools, 3 agents, and test funding and each trade type."""
    # TODO DRY this up, e.g., doing the same calls while swapping the agent.

    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 365,  # 1 year
    )
    # Launches 2 pools on the same local chain
    hyperdrive0 = LocalHyperdrive(fast_chain_fixture, initial_pool_config)
    hyperdrive1 = LocalHyperdrive(fast_chain_fixture, initial_pool_config)

    # Generate funded trading agents from the interactive object
    # Names are reflected on output data frames and plots later
    hyperdrive_agent_0 = fast_chain_fixture.init_agent(
        base=FixedPoint(1_111_111), eth=FixedPoint(111), pool=hyperdrive0, name="alice"
    )
    hyperdrive_agent_1 = fast_chain_fixture.init_agent(
        base=FixedPoint(222_222), eth=FixedPoint(222), pool=hyperdrive1, name="bob"
    )
    # Omission of name defaults to wallet address
    hyperdrive_agent_2 = fast_chain_fixture.init_agent(eth=FixedPoint(10))

    hyperdrive_agent_2.set_active(pool=hyperdrive0)

    # Add funds to an agent
    hyperdrive_agent_2.add_funds(base=FixedPoint(333_333), eth=FixedPoint(333))

    # Ensure agent wallet have expected balances
    assert (hyperdrive_agent_0.get_wallet().balance.amount) == FixedPoint(1_111_111)
    assert (hyperdrive_agent_1.get_wallet().balance.amount) == FixedPoint(222_222)
    assert (hyperdrive_agent_2.get_wallet().balance.amount) == FixedPoint(333_333)
    # Ensure chain balances are as expected
    (
        chain_eth_balance,
        chain_base_balance,
    ) = hyperdrive0.interface.get_eth_base_balances(hyperdrive_agent_0.account)
    assert chain_base_balance == FixedPoint(1_111_111)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    assert (FixedPoint(111) - chain_eth_balance) < FixedPoint("0.0001")
    (
        chain_eth_balance,
        chain_base_balance,
    ) = hyperdrive1.interface.get_eth_base_balances(hyperdrive_agent_1.account)
    assert chain_base_balance == FixedPoint(222_222)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    assert (FixedPoint(222) - chain_eth_balance) < FixedPoint("0.0001")
    (
        chain_eth_balance,
        chain_base_balance,
    ) = hyperdrive0.interface.get_eth_base_balances(hyperdrive_agent_2.account)
    assert chain_base_balance == FixedPoint(333_333)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    # Since we initialized without parameters, and the default is 10 eth. We then added 333 eth.
    assert (FixedPoint(343) - chain_eth_balance) < FixedPoint("0.0001")

    # Test trades
    # We swap back and forth between the two pools, but do comparisons
    # between both pools to ensure bookkeeping is correct on both pools.

    # Add liquidity to 111_111 total
    add_liquidity_event_0 = hyperdrive_agent_0.add_liquidity(base=FixedPoint(111_111))
    assert add_liquidity_event_0.as_base
    assert add_liquidity_event_0.amount == FixedPoint(111_111)
    assert hyperdrive_agent_0.get_wallet().lp_tokens == add_liquidity_event_0.lp_amount
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)
    # TODO run this test once hyperdrive_agent0 gets decoupled from the pool
    # _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_hyperdrive_1, hyperdrive_agent0)

    add_liquidity_event_1 = hyperdrive_agent_1.add_liquidity(base=FixedPoint(111_111))
    assert add_liquidity_event_1.as_base
    assert add_liquidity_event_1.amount == FixedPoint(111_111)
    assert hyperdrive_agent_1.get_wallet().lp_tokens == add_liquidity_event_1.lp_amount
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)

    # Open long
    open_long_event_0 = hyperdrive_agent_0.open_long(base=FixedPoint(22_222))
    assert open_long_event_0.as_base
    assert open_long_event_0.amount == FixedPoint(22_222)
    agent_0_longs = list(hyperdrive_agent_0.get_wallet().longs.values())
    assert len(agent_0_longs) == 1
    assert agent_0_longs[0].balance == open_long_event_0.bond_amount
    assert agent_0_longs[0].maturity_time == open_long_event_0.maturity_time
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)

    open_long_event_1 = hyperdrive_agent_1.open_long(base=FixedPoint(22_222))
    assert open_long_event_1.as_base
    assert open_long_event_1.amount == FixedPoint(22_222)
    agent_1_longs = list(hyperdrive_agent_1.get_wallet().longs.values())
    assert len(agent_1_longs) == 1
    assert agent_1_longs[0].balance == open_long_event_1.bond_amount
    assert agent_1_longs[0].maturity_time == open_long_event_1.maturity_time
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)

    # Remove liquidity
    remove_liquidity_event_0 = hyperdrive_agent_0.remove_liquidity(shares=add_liquidity_event_0.lp_amount)
    assert add_liquidity_event_0.lp_amount == remove_liquidity_event_0.lp_amount
    assert hyperdrive_agent_0.get_wallet().lp_tokens == FixedPoint(0)
    assert hyperdrive_agent_0.get_wallet().withdraw_shares == remove_liquidity_event_0.withdrawal_share_amount
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)

    remove_liquidity_event_1 = hyperdrive_agent_1.remove_liquidity(shares=add_liquidity_event_1.lp_amount)
    assert add_liquidity_event_1.lp_amount == remove_liquidity_event_1.lp_amount
    assert hyperdrive_agent_1.get_wallet().lp_tokens == FixedPoint(0)
    assert hyperdrive_agent_1.get_wallet().withdraw_shares == remove_liquidity_event_1.withdrawal_share_amount
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)

    # We ensure there exists some withdrawal shares that were given from the previous trade for testing purposes
    assert remove_liquidity_event_0.withdrawal_share_amount > 0
    assert remove_liquidity_event_1.withdrawal_share_amount > 0

    # Add liquidity back to ensure we can close positions
    _ = hyperdrive_agent_0.add_liquidity(base=FixedPoint(111_111))
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)

    _ = hyperdrive_agent_1.add_liquidity(base=FixedPoint(111_111))
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)

    # Open short
    open_short_event_0 = hyperdrive_agent_0.open_short(bonds=FixedPoint(333))
    assert open_short_event_0.bond_amount == FixedPoint(333)
    agent_0_shorts = list(hyperdrive_agent_0.get_wallet().shorts.values())
    assert len(agent_0_shorts) == 1
    assert agent_0_shorts[0].balance == open_short_event_0.bond_amount
    assert agent_0_shorts[0].maturity_time == open_short_event_0.maturity_time
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)

    # Open short
    open_short_event_1 = hyperdrive_agent_1.open_short(bonds=FixedPoint(333))
    assert open_short_event_1.bond_amount == FixedPoint(333)
    agent_1_shorts = list(hyperdrive_agent_1.get_wallet().shorts.values())
    assert len(agent_1_shorts) == 1
    assert agent_1_shorts[0].balance == open_short_event_1.bond_amount
    assert agent_1_shorts[0].maturity_time == open_short_event_1.maturity_time
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)

    # Close long
    close_long_event_0 = hyperdrive_agent_0.close_long(
        maturity_time=open_long_event_0.maturity_time, bonds=open_long_event_0.bond_amount
    )
    assert open_long_event_0.bond_amount == close_long_event_0.bond_amount
    assert open_long_event_0.maturity_time == close_long_event_0.maturity_time
    assert len(hyperdrive_agent_0.get_wallet().longs) == 0
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)

    # Close long
    close_long_event_1 = hyperdrive_agent_1.close_long(
        maturity_time=open_long_event_1.maturity_time, bonds=open_long_event_1.bond_amount
    )
    assert open_long_event_1.bond_amount == close_long_event_1.bond_amount
    assert open_long_event_1.maturity_time == close_long_event_1.maturity_time
    assert len(hyperdrive_agent_1.get_wallet().longs) == 0
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)

    # Close short
    close_short_event_0 = hyperdrive_agent_0.close_short(
        maturity_time=open_short_event_0.maturity_time, bonds=open_short_event_0.bond_amount
    )
    assert open_short_event_0.bond_amount == close_short_event_0.bond_amount
    assert open_short_event_0.maturity_time == close_short_event_0.maturity_time
    assert len(hyperdrive_agent_0.get_wallet().shorts) == 0
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)

    # Close short
    close_short_event_1 = hyperdrive_agent_1.close_short(
        maturity_time=open_short_event_1.maturity_time, bonds=open_short_event_1.bond_amount
    )
    assert open_short_event_1.bond_amount == close_short_event_1.bond_amount
    assert open_short_event_1.maturity_time == close_short_event_1.maturity_time
    assert len(hyperdrive_agent_1.get_wallet().shorts) == 0
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)

    # Redeem withdrawal shares
    redeem_event_0 = hyperdrive_agent_0.redeem_withdrawal_share(shares=remove_liquidity_event_0.withdrawal_share_amount)
    assert redeem_event_0.withdrawal_share_amount == remove_liquidity_event_0.withdrawal_share_amount
    assert hyperdrive_agent_0.get_wallet().withdraw_shares == FixedPoint(0)
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive0, hyperdrive_agent_0)

    # Redeem withdrawal shares
    redeem_event_1 = hyperdrive_agent_1.redeem_withdrawal_share(shares=remove_liquidity_event_1.withdrawal_share_amount)
    assert redeem_event_1.withdrawal_share_amount == remove_liquidity_event_1.withdrawal_share_amount
    assert hyperdrive_agent_1.get_wallet().withdraw_shares == FixedPoint(0)
    _ensure_db_wallet_matches_agent_wallet_and_chain(hyperdrive1, hyperdrive_agent_1)


def _to_unscaled_decimal(fp_val: FixedPoint) -> Decimal:
    return Decimal(str(fp_val))


@pytest.mark.anvil
def test_bot_to_db(fast_hyperdrive_fixture: LocalHyperdrive, cycle_trade_policy: Type[CycleTradesPolicy]):
    # Initialize agent
    private_key = make_private_key()
    # We get access to the chain here
    agent = fast_hyperdrive_fixture.chain.init_agent(
        private_key=private_key,
        base=FixedPoint(1_000_000),
        eth=FixedPoint(100),
        pool=fast_hyperdrive_fixture,
        policy=cycle_trade_policy,
        policy_config=cycle_trade_policy.Config(
            slippage_tolerance=FixedPoint("0.0001"),
        ),
    )

    # Run trades
    while not agent.policy_done_trading:
        agent.execute_policy_action()

    # Run bots again, but this time only for 3 trades
    # TODO agent rework will allow us to separate policy from agent
    # but for now, we need to reinitialize another agent with the same
    # key to run the policy from scratch again
    agent = fast_hyperdrive_fixture.chain.init_agent(
        private_key=private_key,
        # We don't add funds here again, as the agent already has funds
        pool=fast_hyperdrive_fixture,
        policy=cycle_trade_policy,
        policy_config=cycle_trade_policy.Config(
            slippage_tolerance=FixedPoint("0.0001"),
            max_trades=3,
        ),
    )

    while not agent.policy_done_trading:
        agent.execute_policy_action()

    # This bot does the following known trades in sequence:
    # 1. addLiquidity of 111_111 base
    # 2. openLong of 22_222 base
    # 3. openShort of 333 bonds
    # 4. removeLiquidity of all LP tokens
    # 5. addLiquidity of 111_111 base
    # 6. closeLong on long from trade 2
    # 7. closeShort on short from trade 3
    # 8. redeemWithdrawalShares of all withdrawal tokens from trade 4
    # The bot then runs again, this time for 3 trades:
    # 9. addLiquidity of 111_111 base
    # 10. openLong of 22_222 base
    # 11. openShort of 333 bonds

    # Test db entries are what we expect
    # We don't coerce to float because we want exact values in decimal

    db_pool_config: pd.Series = fast_hyperdrive_fixture.get_pool_config()

    # TODO these expected values are defined in src/agent0/ethpy/test_fixtures/deploy_hyperdrive.py
    # Eventually, we want to parameterize these values to pass into deploying hyperdrive
    initial_fixed_rate = FixedPoint("0.05")
    # This expected time stretch is only true for 1 year position duration
    expected_timestretch_fp = FixedPoint(1) / (
        FixedPoint("5.24592") / (FixedPoint("0.04665") * (initial_fixed_rate * FixedPoint(100)))
    )
    expected_timestretch = _to_unscaled_decimal(expected_timestretch_fp)
    expected_inv_timestretch = _to_unscaled_decimal((1 / expected_timestretch_fp))
    deployer_address = fast_hyperdrive_fixture.chain.get_deployer_address()
    # pylint: disable=protected-access
    base_token_addr = fast_hyperdrive_fixture.interface.base_token_contract.address
    vault_shares_token_addr = fast_hyperdrive_fixture.interface.vault_shares_token_contract.address
    expected_pool_config = {
        "hyperdrive_address": fast_hyperdrive_fixture.hyperdrive_address,
        "base_token": base_token_addr,
        "vault_shares_token": vault_shares_token_addr,
        "initial_vault_share_price": _to_unscaled_decimal(FixedPoint("1")),
        "minimum_share_reserves": _to_unscaled_decimal(FixedPoint("10")),
        "minimum_transaction_amount": _to_unscaled_decimal(FixedPoint("0.001")),
        "circuit_breaker_delta": _to_unscaled_decimal(FixedPoint("2")),
        "position_duration": 60 * 60 * 24 * 365,  # 1 year
        "checkpoint_duration": 3600,  # 1 hour
        "time_stretch": expected_timestretch,
        "governance": deployer_address,
        "fee_collector": deployer_address,
        "sweep_collector": deployer_address,
        "curve_fee": _to_unscaled_decimal(FixedPoint("0.01")),  # 1%
        "flat_fee": _to_unscaled_decimal(FixedPoint("0.0005")),  # 0.05% APR
        "governance_lp_fee": _to_unscaled_decimal(FixedPoint("0.15")),  # 15%
        "governance_zombie_fee": _to_unscaled_decimal(FixedPoint("0.03")),  # 3%
        "inv_time_stretch": expected_inv_timestretch,
    }

    # We don't care about linker
    db_pool_config = db_pool_config.drop("linker_factory")

    # Ensure keys match
    # Converting to sets and compare
    db_keys = set(db_pool_config.index)
    expected_keys = set(expected_pool_config.keys())
    assert db_keys == expected_keys, "Keys for pool config in db do not match expected"

    # Value comparison
    for key, expected_value in expected_pool_config.items():
        assert_val = db_pool_config[key] == expected_value
        assert assert_val, f"Values in pool config do not match for {key} ({db_pool_config[key]} != {expected_value})"

    # Pool info comparison
    db_pool_info: pd.DataFrame = fast_hyperdrive_fixture.get_pool_info()
    # Compare computed analysis columns vs interface
    # Get the latest entry, then get the relevant columns
    db_latest_pool_info = db_pool_info.iloc[-1]

    pool_state = fast_hyperdrive_fixture.interface.current_pool_state
    expected_pool_info = {
        # Expected indices
        "hyperdrive_address": fast_hyperdrive_fixture.hyperdrive_address,
        "block_number": pool_state.block_number,
        # Pandas converts timestamp to pd.Timestamp, so we do the same here
        "timestamp": pd.Timestamp(pool_state.block_time, unit="s"),
        "epoch_timestamp": pool_state.block_time,
        # Pool Info
        "share_reserves": pool_state.pool_info.share_reserves,
        "share_adjustment": pool_state.pool_info.share_adjustment,
        "zombie_base_proceeds": pool_state.pool_info.zombie_base_proceeds,
        "zombie_share_reserves": pool_state.pool_info.zombie_share_reserves,
        "bond_reserves": pool_state.pool_info.bond_reserves,
        "lp_total_supply": pool_state.pool_info.lp_total_supply,
        "vault_share_price": pool_state.pool_info.vault_share_price,
        "longs_outstanding": pool_state.pool_info.longs_outstanding,
        "long_average_maturity_time": pool_state.pool_info.long_average_maturity_time,
        "shorts_outstanding": pool_state.pool_info.shorts_outstanding,
        "short_average_maturity_time": pool_state.pool_info.short_average_maturity_time,
        "withdrawal_shares_ready_to_withdraw": pool_state.pool_info.withdrawal_shares_ready_to_withdraw,
        "withdrawal_shares_proceeds": pool_state.pool_info.withdrawal_shares_proceeds,
        "lp_share_price": pool_state.pool_info.lp_share_price,
        "long_exposure": pool_state.pool_info.long_exposure,
        # Ethpy Interface Added keys
        "total_supply_withdrawal_shares": pool_state.total_supply_withdrawal_shares,
        "gov_fees_accrued": pool_state.gov_fees_accrued,
        "hyperdrive_base_balance": pool_state.hyperdrive_base_balance,
        "hyperdrive_eth_balance": pool_state.hyperdrive_eth_balance,
        "variable_rate": pool_state.variable_rate,
        "vault_shares": pool_state.vault_shares,
        # Pool analysis keys
        "spot_price": fast_hyperdrive_fixture.interface.calc_spot_price(pool_state),
        "fixed_rate": fast_hyperdrive_fixture.interface.calc_spot_rate(pool_state),
    }
    # Ensure keys match
    # Converting to sets and compare
    db_keys = set(db_latest_pool_info.index)
    expected_keys = set(expected_pool_info.keys())
    assert db_keys == expected_keys, "Keys for pool info in db do not match expected"

    # Value comparison
    for key, expected_value in expected_pool_info.items():
        assert_val = db_latest_pool_info[key] == expected_value
        assert (
            assert_val
        ), f"Values in pool info do not match for {key} ({db_latest_pool_info[key]} != {expected_value})"

    # Compare events in table
    trade_events = agent.get_trade_events(all_token_deltas=False)
    # Ensure trades exist in database
    # Should be 11 total transactions
    expected_number_of_transactions = 11
    assert len(trade_events) == expected_number_of_transactions
    np.testing.assert_array_equal(
        trade_events["event_type"],
        [
            "AddLiquidity",
            "OpenLong",
            "OpenShort",
            "RemoveLiquidity",
            "AddLiquidity",
            "CloseLong",
            "CloseShort",
            "RedeemWithdrawalShares",
            "AddLiquidity",
            "OpenLong",
            "OpenShort",
        ],
    )

    # Get token deltas
    token_deltas = agent.get_trade_events(all_token_deltas=True)
    assert token_deltas["block_number"].nunique() == expected_number_of_transactions
    # 12 different wallet deltas (1 additional since the `RemoveLiquidity` above should be repeated)
    np.testing.assert_array_equal(
        token_deltas["event_type"],
        [
            "AddLiquidity",
            "OpenLong",
            "OpenShort",
            "RemoveLiquidity",
            "RemoveLiquidity",  # This one is duplicated to account for withdrawal shares
            "AddLiquidity",
            "CloseLong",
            "CloseShort",
            "RedeemWithdrawalShares",
            "AddLiquidity",
            "OpenLong",
            "OpenShort",
        ],
    )
    np.testing.assert_array_equal(
        token_deltas["token_type"],
        [
            "LP",
            "LONG",
            "SHORT",
            "LP",
            "WITHDRAWAL_SHARE",
            "LP",
            "LONG",
            "SHORT",
            "WITHDRAWAL_SHARE",
            "LP",
            "LONG",
            "SHORT",
        ],
    )

    # No need to check for token delta correctness,
    # test_funding_and_trades will check for wallet and delta correctness.


@pytest.mark.anvil
def test_block_timestamp_interval(fast_chain_fixture: LocalChain):
    """Ensure block timestamp interval is set correctly."""
    # The chain in the test fixture defaults to 12 seconds

    # We need the underlying hyperdrive interface here to test time
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture)
    hyperdrive_interface = interactive_hyperdrive.interface
    hyperdrive_agent0 = fast_chain_fixture.init_agent(
        base=FixedPoint(1_111_111), eth=FixedPoint(111), pool=interactive_hyperdrive, name="alice"
    )

    current_block_1 = hyperdrive_interface.get_current_block()
    current_time_1 = hyperdrive_interface.get_block_timestamp(current_block_1)

    # Make a trade to mine a block
    hyperdrive_agent0.open_long(base=FixedPoint(111))

    current_block_2 = hyperdrive_interface.get_current_block()
    current_time_2 = hyperdrive_interface.get_block_timestamp(current_block_2)

    # open_long made 2 transactions, 1 approve, and one for the long
    assert "number" in current_block_1
    assert "number" in current_block_2
    block_diff = current_block_2["number"] - current_block_1["number"]
    assert block_diff == 2

    assert (current_time_2 - current_time_1) / block_diff == 12


@pytest.mark.anvil
def test_advance_time(fast_chain_fixture: LocalChain):
    """Advance time by 3600 seconds then 1 week."""
    # We need the underlying hyperdrive interface here to test time
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture)
    hyperdrive_interface = interactive_hyperdrive.interface

    current_time_1 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Testing passing in seconds
    fast_chain_fixture.advance_time(3600, create_checkpoints=False)
    current_time_2 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Testing passing in timedelta
    fast_chain_fixture.advance_time(timedelta(weeks=1), create_checkpoints=False)
    current_time_3 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())

    assert current_time_2 - current_time_1 == 3600
    assert current_time_3 - current_time_2 == 3600 * 24 * 7


@pytest.mark.anvil
def test_advance_time_with_checkpoints(fast_chain_fixture: LocalChain):
    """Checkpoint creation with advance time."""
    # Since advancing time with checkpoints can be off by a block, we set block timestamp interval here
    # to be 1 to avoid advancing extra time
    fast_chain_fixture._set_block_timestamp_interval(1)  # pylint: disable=protected-access

    # We need the underlying hyperdrive interface here to test time
    config = LocalHyperdrive.Config(checkpoint_duration=3600)
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, config)
    hyperdrive_interface = interactive_hyperdrive.interface

    # TODO there is a non-determininstic element here, the first advance time for 600 seconds
    # may push the time forward past a checkpoint boundary depending on the current time,
    # in which case 1 checkpoint will be made. Hence, we can't be certain on how many checkpoints
    # were made per advance time.

    min_time_error = 4  # seconds

    # Advance time lower than a checkpoint duration
    pre_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    checkpoint_events = fast_chain_fixture.advance_time(600, create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    assert abs(post_time - pre_time - 600) <= min_time_error
    # assert 0 or 1 checkpoints made
    assert len(checkpoint_events[interactive_hyperdrive]) in {0, 1}

    # Advance time equal to a checkpoint duration
    pre_time = post_time
    checkpoint_events = fast_chain_fixture.advance_time(3600, create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Advancing time equal to checkpoint duration results in time being off by few second
    assert abs(post_time - pre_time - 3600) <= min_time_error
    # assert one checkpoint made
    assert len(checkpoint_events[interactive_hyperdrive]) in {1, 2}

    # Advance time with multiple checkpoints
    pre_time = post_time
    checkpoint_events = fast_chain_fixture.advance_time(timedelta(hours=3), create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Advancing time equal to checkpoint duration results in time being off by few second
    assert abs(post_time - pre_time - 3600 * 3) <= min_time_error
    # assert 3 checkpoints made
    assert len(checkpoint_events[interactive_hyperdrive]) in {3, 4}

    ## Checking when advancing time of a value not a multiple of checkpoint_duration ##
    pre_time = post_time
    # Advance time with multiple checkpoints
    checkpoint_events = fast_chain_fixture.advance_time(4000, create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Advancing time equal to checkpoint duration results in time being off by few second
    assert abs(post_time - pre_time - 4000) <= min_time_error
    # assert 1 checkpoint made
    assert len(checkpoint_events[interactive_hyperdrive]) in {1, 2}

    # TODO add additional columns in data pipeline for checkpoints from CreateCheckpoint event
    # then check `hyperdrive_interface.get_checkpoint_info` for proper checkpoints.


# We use session chain here to avoid snapshotting since
# we use snapshotting in the test
@pytest.mark.anvil
def test_save_load_snapshot(chain_fixture: LocalChain):
    """Save and load snapshot."""
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    initial_pool_config = LocalHyperdrive.Config()
    interactive_hyperdrive = LocalHyperdrive(chain_fixture, initial_pool_config)
    hyperdrive_interface = interactive_hyperdrive.interface

    # Generate funded trading agents from the interactive object
    # Make trades to set the initial state
    hyperdrive_agent = chain_fixture.init_agent(
        base=FixedPoint(111_111), eth=FixedPoint(111), pool=interactive_hyperdrive, name="alice"
    )
    open_long_event = hyperdrive_agent.open_long(base=FixedPoint(2_222))
    open_short_event = hyperdrive_agent.open_short(bonds=FixedPoint(3_333))
    hyperdrive_agent.add_liquidity(base=FixedPoint(4_444))

    # Save the state on the chain
    chain_fixture.save_snapshot()

    # To ensure snapshots are working, we check the agent's wallet on the chain, the wallet object in the agent,
    # and in the db
    # Check base balance on the chain
    init_eth_on_chain, init_base_on_chain = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.account)
    init_agent_wallet = hyperdrive_agent.get_wallet().copy()
    init_db_wallet = interactive_hyperdrive.get_positions(coerce_float=False).copy()
    init_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    init_pool_state_on_db = interactive_hyperdrive.get_pool_info(coerce_float=False)

    # Make a few trades to change the state
    hyperdrive_agent.close_long(bonds=FixedPoint(222), maturity_time=open_long_event.maturity_time)
    hyperdrive_agent.open_short(bonds=FixedPoint(333))
    hyperdrive_agent.remove_liquidity(shares=FixedPoint(444))

    # Ensure state has changed
    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.account)
    check_agent_wallet = hyperdrive_agent.get_wallet()
    check_db_wallet = interactive_hyperdrive.get_positions(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_info(coerce_float=False)

    assert check_eth_on_chain != init_eth_on_chain
    assert check_base_on_chain != init_base_on_chain
    assert check_agent_wallet != init_agent_wallet
    assert not check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain != init_pool_info_on_chain
    assert not check_pool_state_on_db.equals(init_pool_state_on_db)

    # Save snapshot and check for equality
    chain_fixture.load_snapshot()

    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.account)
    check_agent_wallet = hyperdrive_agent.get_wallet()
    check_db_wallet = interactive_hyperdrive.get_positions(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_info(coerce_float=False)

    assert check_eth_on_chain == init_eth_on_chain
    assert check_base_on_chain == init_base_on_chain
    assert check_agent_wallet == init_agent_wallet
    assert check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain == init_pool_info_on_chain
    assert check_pool_state_on_db.equals(init_pool_state_on_db)

    # Do it again to make sure we can do multiple loads

    # Make a few trades to change the state
    hyperdrive_agent.open_long(base=FixedPoint(222))
    hyperdrive_agent.close_short(bonds=FixedPoint(333), maturity_time=open_short_event.maturity_time)
    hyperdrive_agent.remove_liquidity(shares=FixedPoint(555))

    # Ensure state has changed
    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.account)
    check_agent_wallet = hyperdrive_agent.get_wallet()
    check_db_wallet = interactive_hyperdrive.get_positions(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_info(coerce_float=False)

    assert check_eth_on_chain != init_eth_on_chain
    assert check_base_on_chain != init_base_on_chain
    assert check_agent_wallet != init_agent_wallet
    assert not check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain != init_pool_info_on_chain
    assert not check_pool_state_on_db.equals(init_pool_state_on_db)

    # Save snapshot and check for equality
    chain_fixture.load_snapshot()

    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.account)
    check_agent_wallet = hyperdrive_agent.get_wallet()
    check_db_wallet = interactive_hyperdrive.get_positions(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_info(coerce_float=False)

    assert check_eth_on_chain == init_eth_on_chain
    assert check_base_on_chain == init_base_on_chain
    assert check_agent_wallet == init_agent_wallet
    assert check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain == init_pool_info_on_chain
    assert check_pool_state_on_db.equals(init_pool_state_on_db)

    # Do it again to make sure we can do multiple loads

    # Make a few trades to change the state
    hyperdrive_agent.open_long(base=FixedPoint(222))
    hyperdrive_agent.close_short(bonds=FixedPoint(333), maturity_time=open_short_event.maturity_time)
    hyperdrive_agent.remove_liquidity(shares=FixedPoint(555))

    # Ensure state has changed
    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.account)
    check_agent_wallet = hyperdrive_agent.get_wallet()
    check_db_wallet = interactive_hyperdrive.get_positions(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_info(coerce_float=False)

    assert check_eth_on_chain != init_eth_on_chain
    assert check_base_on_chain != init_base_on_chain
    assert check_agent_wallet != init_agent_wallet
    assert not check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain != init_pool_info_on_chain
    assert not check_pool_state_on_db.equals(init_pool_state_on_db)

    # Save snapshot and check for equality
    chain_fixture.load_snapshot()

    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.account)
    check_agent_wallet = hyperdrive_agent.get_wallet()
    check_db_wallet = interactive_hyperdrive.get_positions(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_info(coerce_float=False)

    assert check_eth_on_chain == init_eth_on_chain
    assert check_base_on_chain == init_base_on_chain
    assert check_agent_wallet == init_agent_wallet
    assert check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain == init_pool_info_on_chain
    assert check_pool_state_on_db.equals(init_pool_state_on_db)


@pytest.mark.anvil
def test_set_variable_rate(fast_chain_fixture: LocalChain):
    """Set the variable rate."""
    # We need the underlying hyperdrive interface here to test time
    config = LocalHyperdrive.Config(initial_variable_rate=FixedPoint("0.05"))
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, config)

    # Make a trade to mine the block on this variable rate so it shows up in the data pipeline
    _ = fast_chain_fixture.init_agent(eth=FixedPoint(10), pool=interactive_hyperdrive)

    # Set the variable rate
    # This mines a block since it's a transaction
    interactive_hyperdrive.set_variable_rate(FixedPoint("0.10"))

    # Ensure variable rate has changed
    pool_state_df = interactive_hyperdrive.get_pool_info(coerce_float=False)

    assert pool_state_df["variable_rate"].iloc[0] == Decimal("0.05")
    assert pool_state_df["variable_rate"].iloc[-1] == Decimal("0.10")


@pytest.mark.anvil
def test_dashboard_dfs(fast_hyperdrive_fixture: LocalHyperdrive):
    """Tests building of dashboard dataframes."""

    # Build an agent and make random trades
    agent0 = fast_hyperdrive_fixture.chain.init_agent(
        base=FixedPoint(1_000_000),
        eth=FixedPoint(100),
        name="random_bot_0",
        pool=fast_hyperdrive_fixture,
        # The underlying policy to attach to this agent
        policy=PolicyZoo.random,
        # The configuration for the underlying policy
        policy_config=PolicyZoo.random.Config(rng_seed=123),
    )
    agent1 = fast_hyperdrive_fixture.chain.init_agent(
        base=FixedPoint(1_000_000),
        eth=FixedPoint(100),
        name="random_bot_1",
        pool=fast_hyperdrive_fixture,
        # The underlying policy to attach to this agent
        policy=PolicyZoo.random,
        # The configuration for the underlying policy
        policy_config=PolicyZoo.random.Config(rng_seed=456),
    )

    # Add liquidity to avoid insufficient liquidity error
    agent0.add_liquidity(base=FixedPoint(800_000))

    for _ in range(10):
        # NOTE Since a policy can execute multiple trades per action, the output events is a list
        agent0.execute_policy_action()
        agent1.execute_policy_action()

    # Ensure dataframes can be built
    build_pool_dashboard(fast_hyperdrive_fixture.hyperdrive_address, fast_hyperdrive_fixture.chain.db_session)
    build_wallet_dashboard([agent0.address, agent1.address], fast_hyperdrive_fixture.chain.db_session)


@pytest.mark.anvil
def test_access_deployer_account(fast_chain_fixture: LocalChain):
    """Access the deployer account."""
    config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint("100"),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, config)
    privkey = fast_chain_fixture.get_deployer_account_private_key()  # anvil account 0
    pubkey = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    larry = fast_chain_fixture.init_agent(
        base=FixedPoint(100_000), eth=FixedPoint(10), name="larry", pool=interactive_hyperdrive, private_key=privkey
    )
    larry_pubkey = larry.address
    assert larry_pubkey == pubkey  # deployer public key


@pytest.mark.anvil
def test_access_deployer_liquidity(fast_chain_fixture: LocalChain):
    """Remove liquidity from the deployer account."""
    config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(100),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, config)
    privkey = fast_chain_fixture.get_deployer_account_private_key()  # anvil account 0
    larry = fast_chain_fixture.init_agent(
        base=FixedPoint(100_000), eth=FixedPoint(10), name="larry", pool=interactive_hyperdrive, private_key=privkey
    )
    assert (
        FixedPoint(
            scaled_value=interactive_hyperdrive.interface.hyperdrive_contract.functions.balanceOf(
                encode_asset_id(AssetIdPrefix.LP, 0),
                larry.address,
            ).call()
        )
        == larry.get_wallet().lp_tokens
    )
    # Hyperdrive pool steals 2 * minimumShareReserves from the initial deployer's liquidity
    assert larry.get_wallet().lp_tokens == config.initial_liquidity - 2 * config.minimum_share_reserves


@pytest.mark.anvil
def test_remove_deployer_liquidity(fast_chain_fixture: LocalChain):
    """Remove liquidity from the deployer account."""
    config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(100),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, config)
    privkey = fast_chain_fixture.get_deployer_account_private_key()  # anvil account 0
    larry = fast_chain_fixture.init_agent(
        base=FixedPoint(100_000), eth=FixedPoint(10), name="larry", pool=interactive_hyperdrive, private_key=privkey
    )
    larry.remove_liquidity(shares=larry.get_wallet().lp_tokens)
    assert larry.get_wallet().lp_tokens == 0
    assert (
        FixedPoint(
            scaled_value=interactive_hyperdrive.interface.hyperdrive_contract.functions.balanceOf(
                encode_asset_id(AssetIdPrefix.LP, 0),
                larry.address,
            ).call()
        )
        == 0
    )


@pytest.mark.anvil
def test_get_config_no_transactions(fast_chain_fixture: LocalChain):
    """Get pool config before executing any transactions."""
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture)
    pool_config = interactive_hyperdrive.get_pool_config()
    assert isinstance(pool_config, Series)


@pytest.mark.anvil
def test_get_config_with_transactions(fast_chain_fixture: LocalChain):
    """Get pool config after executing one transaction."""
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture)
    agent0 = fast_chain_fixture.init_agent(
        base=FixedPoint(100_000), eth=FixedPoint(100), pool=interactive_hyperdrive, name="alice"
    )
    agent0.open_long(base=FixedPoint(11_111))
    pool_config = interactive_hyperdrive.get_pool_config()
    assert isinstance(pool_config, Series)


@pytest.mark.anvil
def test_liquidate(fast_chain_fixture: LocalChain):
    """Test liquidation."""
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture)
    alice = fast_chain_fixture.init_agent(
        base=FixedPoint(10_000), eth=FixedPoint(10), pool=interactive_hyperdrive, name="alice"
    )
    alice.open_long(base=FixedPoint(100))
    alice.open_short(bonds=FixedPoint(100))
    alice.add_liquidity(base=FixedPoint(100))
    current_wallet = alice.get_positions()
    assert current_wallet.shape[0] == 3  # we have 3 open positions
    alice.liquidate()
    current_wallet = alice.get_positions()
    assert current_wallet.shape[0] == 0  # we have 0 open position


@pytest.mark.anvil
def test_random_liquidate(fast_chain_fixture: LocalChain):
    """Test random liquidation."""
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture)
    alice = fast_chain_fixture.init_agent(
        base=FixedPoint(10_000), eth=FixedPoint(10), pool=interactive_hyperdrive, name="alice"
    )

    # We run the same trades 5 times, and ensure there's at least one difference
    # between the 5 liquidations.
    all_liquidate_events = []
    for _ in range(5):
        alice.open_long(base=FixedPoint(100))
        alice.open_short(bonds=FixedPoint(100))
        alice.add_liquidity(base=FixedPoint(100))
        current_wallet = interactive_hyperdrive.get_positions()
        assert current_wallet.shape[0] == 4  # we have 4 open positions, including base
        liquidate_events = alice.liquidate(randomize=True)
        # We run liquidate here twice, as there's a chance the trades result in gaining withdrawal shares
        # TODO write loop within liquidate to call this multiple times
        # and also account for when no withdrawal shares are available to withdraw.
        liquidate_events.extend(alice.liquidate(randomize=True))
        current_wallet = interactive_hyperdrive.get_positions()
        all_liquidate_events.append(liquidate_events)
        assert current_wallet.shape[0] == 1  # we have 1 open position, including base
    assert len(all_liquidate_events) == 5
    # We ensure not all trades are identical
    is_different = False
    check_events = all_liquidate_events[0]
    for events in all_liquidate_events[1:]:
        # Check length, if different we're done
        # (due to withdrawal shares event)
        if len(check_events) != len(events):
            is_different = True
            break
        for check_event, event in zip(check_events, events):
            if check_event != event:
                is_different = True
                break

    if not is_different:
        raise ValueError("Random liquidation resulted in the same trades")


@pytest.mark.anvil
def test_share_price_compounding_quincunx(fast_chain_fixture: LocalChain):
    """Share price when compounding by quincunx (one fifth of a year) should increase by more than the APR."""
    # setup
    initial_variable_rate = FixedPoint("0.045")
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0),
        curve_fee=FixedPoint(0),
        flat_fee=FixedPoint(0),
        initial_variable_rate=initial_variable_rate,
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    logging.info(f"Variable rate: {hyperdrive_interface.current_pool_state.variable_rate}")
    logging.info(f"Starting share price: {hyperdrive_interface.current_pool_state.pool_info.lp_share_price}")
    number_of_compounding_periods = 5
    for _ in range(number_of_compounding_periods):
        fast_chain_fixture.advance_time(YEAR_IN_SECONDS // number_of_compounding_periods, create_checkpoints=False)
        # This calls the mock yield source's accrue interest function, which acts to compound return
        interactive_hyperdrive._create_checkpoint()  # pylint: disable=protected-access
    ending_share_price = hyperdrive_interface.current_pool_state.pool_info.lp_share_price
    logging.info(f"Ending   share price: {ending_share_price}")
    assert ending_share_price - 1 > initial_variable_rate, (
        f"Expected ending share price to be {float(initial_variable_rate)}, got {float(ending_share_price-1)}"
        f" with a difference of {float(ending_share_price-1-initial_variable_rate)} "
        f"({float((ending_share_price-1-initial_variable_rate)/initial_variable_rate):.2f}%)"
    )


@pytest.mark.anvil
def test_share_price_compounding_annus(fast_chain_fixture: LocalChain):
    """Share price when compounding by annus (one year) should increase by exactly the APR (no compounding)."""
    # setup
    initial_variable_rate = FixedPoint("0.045")
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0),
        curve_fee=FixedPoint(0),
        flat_fee=FixedPoint(0),
        initial_variable_rate=initial_variable_rate,
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    beginning_share_price = hyperdrive_interface.current_pool_state.pool_info.lp_share_price
    logging.info(f"Variable rate: {hyperdrive_interface.current_pool_state.variable_rate}")
    logging.info(f"Starting share price: {beginning_share_price}")
    fast_chain_fixture.advance_time(YEAR_IN_SECONDS, create_checkpoints=False)
    ending_share_price = hyperdrive_interface.current_pool_state.pool_info.lp_share_price
    logging.info(f"Ending   share price: {ending_share_price}")
    assert ending_share_price - beginning_share_price == initial_variable_rate


@pytest.mark.anvil
def test_policy_config_forgotten(fast_chain_fixture: LocalChain):
    """The policy config is not passed in."""
    interactive_config = LocalHyperdrive.Config()
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    alice = fast_chain_fixture.init_agent(
        base=FixedPoint(10_000),
        eth=FixedPoint(10),
        pool=interactive_hyperdrive,
        name="alice",
        policy=PolicyZoo.random,
    )
    assert alice._active_policy is not None


@pytest.mark.anvil
def test_policy_config_none_rng(fast_chain_fixture: LocalChain):
    """The policy config has rng set to None."""
    interactive_config = LocalHyperdrive.Config()
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    agent_policy = PolicyZoo.random.Config()
    agent_policy.rng = None
    alice = fast_chain_fixture.init_agent(
        base=FixedPoint(10_000),
        eth=FixedPoint(10),
        pool=interactive_hyperdrive,
        name="alice",
        policy=PolicyZoo.random,
        policy_config=agent_policy,
    )
    assert alice._active_policy is not None
    assert alice._active_policy.rng is not None


@pytest.mark.anvil
def test_pool_creation_after_snapshot(chain_fixture: LocalChain):
    # pylint: disable=protected-access
    assert len(chain_fixture._deployed_hyperdrive_pools) == 0
    chain_fixture.save_snapshot()
    _ = LocalHyperdrive(chain_fixture)
    assert len(chain_fixture._deployed_hyperdrive_pools) == 1
    chain_fixture.load_snapshot()
    assert len(chain_fixture._deployed_hyperdrive_pools) == 0
    _ = LocalHyperdrive(chain_fixture)
    chain_fixture.save_snapshot()
    _ = LocalHyperdrive(chain_fixture)
    assert len(chain_fixture._deployed_hyperdrive_pools) == 2
    chain_fixture.load_snapshot()
    assert len(chain_fixture._deployed_hyperdrive_pools) == 1


# Since we use snapshots in test fixtures, we can't use the fixture here
# So we build from scratch
@pytest.mark.anvil
def test_snapshot_policy_state(chain_fixture: LocalChain):
    """Tests proper saving/loading of policy state during snapshotting."""

    # Define dummy class for deep state copy
    class _InnerState:
        inner_var: int

        def __init__(self):
            self.inner_var = 1
            self.inner_list = [1]

    class _SubPolicy(HyperdriveBasePolicy):
        inner_state: _InnerState
        outer_var: int

        def __init__(self, policy_config: HyperdriveBasePolicy.Config):
            self.inner_state = _InnerState()
            self.outer_var = 2
            self.outer_list = [2]
            super().__init__(policy_config)

        def action(
            self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
        ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
            # pylint: disable=missing-return-doc
            return [], False

    # Initialize agent with sub policy
    interactive_hyperdrive = LocalHyperdrive(chain_fixture)
    agent = chain_fixture.init_agent(eth=FixedPoint(10), pool=interactive_hyperdrive, policy=_SubPolicy)
    # Snapshot state
    chain_fixture.save_snapshot()

    # Sanity check and type narrowing
    assert isinstance(agent._active_policy, _SubPolicy)
    assert agent._active_policy.outer_var == 2
    assert agent._active_policy.outer_list == [2]
    assert agent._active_policy.inner_state.inner_var == 1
    assert agent._active_policy.inner_state.inner_list == [1]

    # Change inner state variables
    agent._active_policy.outer_var = 22
    agent._active_policy.outer_list.append(222)
    agent._active_policy.inner_state.inner_var = 11
    agent._active_policy.inner_state.inner_list.append(111)
    assert agent._active_policy.outer_var == 22
    assert agent._active_policy.outer_list == [2, 222]
    assert agent._active_policy.inner_state.inner_var == 11
    assert agent._active_policy.inner_state.inner_list == [1, 111]

    # Load snapshot
    chain_fixture.load_snapshot()

    # Ensure inner states were restored
    assert agent._active_policy.outer_var == 2
    assert agent._active_policy.outer_list == [2]
    assert agent._active_policy.inner_state.inner_var == 1
    assert agent._active_policy.inner_state.inner_list == [1]


@pytest.mark.anvil
def test_load_rng_on_snapshot():
    """The policy config has rng set to None."""
    load_rng_chain = LocalChain(config=LocalChain.Config(chain_port=6000, db_port=6001, load_rng_on_snapshot=True))
    non_load_rng_chain = LocalChain(config=LocalChain.Config(chain_port=6002, db_port=6003, load_rng_on_snapshot=False))

    agent_policy = PolicyZoo.random.Config()
    agent_policy.rng = None

    alice = load_rng_chain.init_agent(
        eth=FixedPoint(10),
        name="alice",
        policy=PolicyZoo.random,
        policy_config=agent_policy,
    )
    bob = non_load_rng_chain.init_agent(
        eth=FixedPoint(10),
        name="bob",
        policy=PolicyZoo.random,
        policy_config=agent_policy,
    )

    load_rng_chain.save_snapshot()
    non_load_rng_chain.save_snapshot()

    assert alice._active_policy is not None
    assert alice._active_policy.rng is not None
    assert bob._active_policy is not None
    assert bob._active_policy.rng is not None

    alice_random_before_snap = alice._active_policy.rng.standard_normal(10)
    bob_random_before_snap = bob._active_policy.rng.standard_normal(10)

    load_rng_chain.load_snapshot()
    non_load_rng_chain.load_snapshot()

    alice_random_after_snap = alice._active_policy.rng.standard_normal(10)
    bob_random_after_snap = bob._active_policy.rng.standard_normal(10)

    assert np.array_equal(alice_random_before_snap, alice_random_after_snap)
    assert not np.array_equal(bob_random_before_snap, bob_random_after_snap)

    load_rng_chain.cleanup()
    non_load_rng_chain.cleanup()


def test_hyperdrive_read_interface_standardized_variable_rate(fast_chain_fixture: LocalChain):
    # TODO this is testing the underlying standardized_variable_rate call in
    # the hyperdrive interface. Ideally, this would live in `read_interface_test.py`,
    # but we need a local chain for advancing time for testing. Move this test
    # to `read_interface_test` once we start using interactive hyperdrive for all tests.

    hyperdrive_config = LocalHyperdrive.Config(checkpoint_duration=86400)  # checkpoint duration of 1 day
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, hyperdrive_config)
    hyperdrive_interface = interactive_hyperdrive.interface

    mock_variable_rate = hyperdrive_interface.get_variable_rate()

    # This should fail since pool was just deloyed
    with pytest.raises(ValueError):
        hyperdrive_interface.get_standardized_variable_rate(time_range=604800)  # Get var rate for 1 week

    # Advance time by 8 days, past time_range
    fast_chain_fixture.advance_time(timedelta(days=8), create_checkpoints=True)

    standardized_variable_rate = hyperdrive_interface.get_standardized_variable_rate(time_range=604800)

    assert isclose(mock_variable_rate, standardized_variable_rate, abs_tol=FixedPoint("1e-5"))


@pytest.mark.anvil
@pytest.mark.parametrize("time_stretch", [0.01, 0.1, 0.5, 1, 10, 100])
def test_deploy_nonstandard_timestretch(fast_chain_fixture: LocalChain, time_stretch: float):
    """Deploy with nonstandard timestretch parameters."""
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(10_000_000),
        position_duration=60 * 60 * 24 * 365,  # 1 year
        factory_min_fixed_apr=FixedPoint(0.001),
        factory_max_fixed_apr=FixedPoint(1000),
        factory_min_time_stretch_apr=FixedPoint(0.001),
        factory_max_time_stretch_apr=FixedPoint(1000),
        initial_fixed_apr=FixedPoint(time_stretch),
        initial_time_stretch_apr=FixedPoint(time_stretch),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)
    assert isinstance(interactive_hyperdrive.interface.current_pool_state.pool_config.time_stretch, FixedPoint)
