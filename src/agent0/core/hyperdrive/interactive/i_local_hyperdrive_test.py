"""Tests interactive hyperdrive end to end."""

import datetime
import logging
from decimal import Decimal

import pytest
from fixedpointmath import FixedPoint
from pandas import Series

from agent0.core.hyperdrive import HyperdriveWallet
from agent0.ethpy.hyperdrive import BASE_TOKEN_SYMBOL, AssetIdPrefix, encode_asset_id

from .i_local_chain import ILocalChain
from .i_local_hyperdrive import ILocalHyperdrive

YEAR_IN_SECONDS = 31_536_000

# needed to pass in fixtures
# pylint: disable=redefined-outer-name
# ruff: noqa: PLR2004 (comparison against magic values (literals like numbers))
# allow non-lazy logging
# pylint: disable=logging-fstring-interpolation


@pytest.mark.anvil
def _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive: ILocalHyperdrive, agent_wallet: HyperdriveWallet):
    # NOTE this function is assuming only one agent is making trades

    # Test against db
    current_wallet_df = interactive_hyperdrive.get_current_wallet(coerce_float=False)

    base_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == BASE_TOKEN_SYMBOL]
    assert len(base_wallet_df) == 1
    assert agent_wallet.balance.amount == FixedPoint(base_wallet_df.iloc[0]["position"])

    # Check lp
    lp_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "LP"]
    if len(lp_wallet_df) == 0:
        check_value = FixedPoint(0)
    elif len(lp_wallet_df) == 1:
        check_value = FixedPoint(lp_wallet_df.iloc[0]["position"])
    else:
        assert False
    assert check_value == agent_wallet.lp_tokens

    # Check longs
    long_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "LONG"]
    assert len(long_wallet_df) == len(agent_wallet.longs)
    for _, long_df in long_wallet_df.iterrows():
        assert long_df["maturity_time"] in agent_wallet.longs
        assert agent_wallet.longs[long_df["maturity_time"]].balance == long_df["position"]

    # Check shorts
    short_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "SHORT"]
    assert len(short_wallet_df) == len(agent_wallet.shorts)
    for _, short_df in short_wallet_df.iterrows():
        assert short_df["maturity_time"] in agent_wallet.shorts
        assert agent_wallet.shorts[short_df["maturity_time"]].balance == short_df["position"]

    # Check withdrawal_shares
    withdrawal_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "WITHDRAWAL_SHARE"]
    if len(withdrawal_wallet_df) == 0:
        check_value = FixedPoint(0)
    elif len(withdrawal_wallet_df) == 1:
        check_value = FixedPoint(withdrawal_wallet_df.iloc[0]["position"])
    else:
        assert False
    assert check_value == agent_wallet.withdraw_shares


# Lots of things to test
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# ruff: noqa: PLR0915 (too many statements)
@pytest.mark.anvil
def test_funding_and_trades(chain: ILocalChain):
    """Deploy 2 pools, 3 agents, and test funding and each trade type."""
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = ILocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 365,  # 1 year
    )
    # Launches 2 pools on the same local chain
    interactive_hyperdrive = ILocalHyperdrive(chain, initial_pool_config)
    interactive_hyperdrive_2 = ILocalHyperdrive(chain, initial_pool_config)

    # Generate funded trading agents from the interactive object
    # Names are reflected on output data frames and plots later
    hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(1_111_111), eth=FixedPoint(111), name="alice")
    hyperdrive_agent1 = interactive_hyperdrive_2.init_agent(base=FixedPoint(222_222), eth=FixedPoint(222), name="bob")
    # Omission of name defaults to wallet address
    hyperdrive_agent2 = interactive_hyperdrive.init_agent()

    # Add funds to an agent
    hyperdrive_agent2.add_funds(base=FixedPoint(333_333), eth=FixedPoint(333))

    # Ensure agent wallet have expected balances
    assert (hyperdrive_agent0.wallet.balance.amount) == FixedPoint(1_111_111)
    assert (hyperdrive_agent1.wallet.balance.amount) == FixedPoint(222_222)
    assert (hyperdrive_agent2.wallet.balance.amount) == FixedPoint(333_333)
    # Ensure chain balances are as expected
    (
        chain_eth_balance,
        chain_base_balance,
    ) = interactive_hyperdrive.interface.get_eth_base_balances(hyperdrive_agent0.agent)
    assert chain_base_balance == FixedPoint(1_111_111)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    assert (FixedPoint(111) - chain_eth_balance) < FixedPoint("0.0001")
    (
        chain_eth_balance,
        chain_base_balance,
    ) = interactive_hyperdrive_2.interface.get_eth_base_balances(hyperdrive_agent1.agent)
    assert chain_base_balance == FixedPoint(222_222)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    assert (FixedPoint(222) - chain_eth_balance) < FixedPoint("0.0001")
    (
        chain_eth_balance,
        chain_base_balance,
    ) = interactive_hyperdrive.interface.get_eth_base_balances(hyperdrive_agent2.agent)
    assert chain_base_balance == FixedPoint(333_333)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    # Since we initialized without parameters, and the default is 10 eth. We then added 333 eth.
    assert (FixedPoint(343) - chain_eth_balance) < FixedPoint("0.0001")

    # Test trades
    # Add liquidity to 112_111 total
    add_liquidity_event = hyperdrive_agent0.add_liquidity(base=FixedPoint(111_111))
    assert add_liquidity_event.base_amount == FixedPoint(111_111)
    assert hyperdrive_agent0.wallet.lp_tokens == add_liquidity_event.lp_amount
    _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

    # Open long
    open_long_event = hyperdrive_agent0.open_long(base=FixedPoint(22_222))
    assert open_long_event.base_amount == FixedPoint(22_222)
    agent0_longs = list(hyperdrive_agent0.wallet.longs.values())
    assert len(agent0_longs) == 1
    assert agent0_longs[0].balance == open_long_event.bond_amount
    assert agent0_longs[0].maturity_time == open_long_event.maturity_time
    _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

    # Remove liquidity
    remove_liquidity_event = hyperdrive_agent0.remove_liquidity(shares=add_liquidity_event.lp_amount)
    assert add_liquidity_event.lp_amount == remove_liquidity_event.lp_amount
    assert hyperdrive_agent0.wallet.lp_tokens == FixedPoint(0)
    assert hyperdrive_agent0.wallet.withdraw_shares == remove_liquidity_event.withdrawal_share_amount
    _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

    # We ensure there exists some withdrawal shares that were given from the previous trade for testing purposes
    assert remove_liquidity_event.withdrawal_share_amount > 0

    # Open short
    open_short_event = hyperdrive_agent0.open_short(bonds=FixedPoint(333))
    assert open_short_event.bond_amount == FixedPoint(333)
    agent0_shorts = list(hyperdrive_agent0.wallet.shorts.values())
    assert len(agent0_shorts) == 1
    assert agent0_shorts[0].balance == open_short_event.bond_amount
    assert agent0_shorts[0].maturity_time == open_short_event.maturity_time
    _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

    # Close long
    close_long_event = hyperdrive_agent0.close_long(
        maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
    )
    assert open_long_event.bond_amount == close_long_event.bond_amount
    assert open_long_event.maturity_time == close_long_event.maturity_time
    assert len(hyperdrive_agent0.wallet.longs) == 0
    _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

    # Close short
    close_short_event = hyperdrive_agent0.close_short(
        maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
    )
    assert open_short_event.bond_amount == close_short_event.bond_amount
    assert open_short_event.maturity_time == close_short_event.maturity_time
    assert len(hyperdrive_agent0.wallet.shorts) == 0
    _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

    # Redeem withdrawal shares
    redeem_event = hyperdrive_agent0.redeem_withdraw_share(shares=remove_liquidity_event.withdrawal_share_amount)
    assert redeem_event.withdrawal_share_amount == remove_liquidity_event.withdrawal_share_amount
    assert hyperdrive_agent0.wallet.withdraw_shares == FixedPoint(0)
    _ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)


@pytest.mark.anvil
def test_block_timestamp_interval(chain: ILocalChain):
    """Ensure block timestamp interval is set correctly."""
    # The chain in the test fixture defaults to 12 seconds

    # We need the underlying hyperdrive interface here to test time
    interactive_hyperdrive = ILocalHyperdrive(chain)
    hyperdrive_interface = interactive_hyperdrive.interface
    hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(1_111_111), eth=FixedPoint(111), name="alice")

    current_time_1 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())

    # Make a trade to mine a block
    hyperdrive_agent0.open_long(base=FixedPoint(111))

    current_time_2 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())

    assert current_time_2 - current_time_1 == 12


@pytest.mark.anvil
def test_advance_time(chain: ILocalChain):
    """Advance time by 3600 seconds then 1 week."""
    # We need the underlying hyperdrive interface here to test time
    interactive_hyperdrive = ILocalHyperdrive(chain)
    hyperdrive_interface = interactive_hyperdrive.interface

    current_time_1 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Testing passing in seconds
    chain.advance_time(3600, create_checkpoints=False)
    current_time_2 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Testing passing in timedelta
    chain.advance_time(datetime.timedelta(weeks=1), create_checkpoints=False)
    current_time_3 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())

    assert current_time_2 - current_time_1 == 3600
    assert current_time_3 - current_time_2 == 3600 * 24 * 7


@pytest.mark.anvil
def test_advance_time_with_checkpoints(chain: ILocalChain):
    """Checkpoint creation with advance time."""
    # Since advancing time with checkpoints can be off by a block, we set block timestamp interval here
    # to be 1 to avoid advancing extra time
    chain._set_block_timestamp_interval(1)  # pylint: disable=protected-access

    # We need the underlying hyperdrive interface here to test time
    config = ILocalHyperdrive.Config(checkpoint_duration=3600)
    interactive_hyperdrive = ILocalHyperdrive(chain, config)
    hyperdrive_interface = interactive_hyperdrive.interface

    # TODO there is a non-determininstic element here, the first advance time for 600 seconds
    # may push the time forward past a checkpoint boundary depending on the current time,
    # in which case 1 checkpoint will be made. Hence, we can't be certain on how many checkpoints
    # were made per advance time.

    min_time_error = 4  # seconds

    # Advance time lower than a checkpoint duration
    pre_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    checkpoint_events = chain.advance_time(600, create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    assert abs(post_time - pre_time - 600) <= min_time_error
    # assert 0 or 1 checkpoints made
    assert len(checkpoint_events[interactive_hyperdrive]) in {0, 1}

    # Advance time equal to a checkpoint duration
    pre_time = post_time
    checkpoint_events = chain.advance_time(3600, create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Advancing time equal to checkpoint duration results in time being off by few second
    assert abs(post_time - pre_time - 3600) <= min_time_error
    # assert one checkpoint made
    assert len(checkpoint_events[interactive_hyperdrive]) in {1, 2}

    # Advance time with multiple checkpoints
    pre_time = post_time
    checkpoint_events = chain.advance_time(datetime.timedelta(hours=3), create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Advancing time equal to checkpoint duration results in time being off by few second
    assert abs(post_time - pre_time - 3600 * 3) <= min_time_error
    # assert 3 checkpoints made
    assert len(checkpoint_events[interactive_hyperdrive]) in {3, 4}

    ## Checking when advancing time of a value not a multiple of checkpoint_duration ##
    pre_time = post_time
    # Advance time with multiple checkpoints
    checkpoint_events = chain.advance_time(4000, create_checkpoints=True)
    post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
    # Advancing time equal to checkpoint duration results in time being off by few second
    assert abs(post_time - pre_time - 4000) <= min_time_error
    # assert 1 checkpoint made
    assert len(checkpoint_events[interactive_hyperdrive]) in {1, 2}

    # TODO add additional columns in data pipeline for checkpoints from CreateCheckpoint event
    # then check `hyperdrive_interface.get_checkpoint_info` for proper checkpoints.


@pytest.mark.anvil
def test_save_load_snapshot(chain: ILocalChain):
    """Save and load snapshot."""
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    initial_pool_config = ILocalHyperdrive.Config()
    interactive_hyperdrive = ILocalHyperdrive(chain, initial_pool_config)
    hyperdrive_interface = interactive_hyperdrive.interface

    # Generate funded trading agents from the interactive object
    # Make trades to set the initial state
    hyperdrive_agent = interactive_hyperdrive.init_agent(base=FixedPoint(111_111), eth=FixedPoint(111), name="alice")
    open_long_event = hyperdrive_agent.open_long(base=FixedPoint(2_222))
    open_short_event = hyperdrive_agent.open_short(bonds=FixedPoint(3_333))
    hyperdrive_agent.add_liquidity(base=FixedPoint(4_444))

    # Save the state on the chain
    chain.save_snapshot()

    # To ensure snapshots are working, we check the agent's wallet on the chain, the wallet object in the agent,
    # and in the db
    # Check base balance on the chain
    init_eth_on_chain, init_base_on_chain = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
    init_agent_wallet = hyperdrive_agent.wallet.copy()
    init_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False).copy()
    init_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    init_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

    # Make a few trades to change the state
    hyperdrive_agent.close_long(bonds=FixedPoint(222), maturity_time=open_long_event.maturity_time)
    hyperdrive_agent.open_short(bonds=FixedPoint(333))
    hyperdrive_agent.remove_liquidity(shares=FixedPoint(444))

    # Ensure state has changed
    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
    check_agent_wallet = hyperdrive_agent.wallet
    check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

    assert check_eth_on_chain != init_eth_on_chain
    assert check_base_on_chain != init_base_on_chain
    assert check_agent_wallet != init_agent_wallet
    assert not check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain != init_pool_info_on_chain
    assert not check_pool_state_on_db.equals(init_pool_state_on_db)

    # Save snapshot and check for equality
    chain.load_snapshot()

    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
    check_agent_wallet = hyperdrive_agent.wallet
    check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

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
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
    check_agent_wallet = hyperdrive_agent.wallet
    check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

    assert check_eth_on_chain != init_eth_on_chain
    assert check_base_on_chain != init_base_on_chain
    assert check_agent_wallet != init_agent_wallet
    assert not check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain != init_pool_info_on_chain
    assert not check_pool_state_on_db.equals(init_pool_state_on_db)

    # Save snapshot and check for equality
    chain.load_snapshot()

    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
    check_agent_wallet = hyperdrive_agent.wallet
    check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

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
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
    check_agent_wallet = hyperdrive_agent.wallet
    check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

    assert check_eth_on_chain != init_eth_on_chain
    assert check_base_on_chain != init_base_on_chain
    assert check_agent_wallet != init_agent_wallet
    assert not check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain != init_pool_info_on_chain
    assert not check_pool_state_on_db.equals(init_pool_state_on_db)

    # Save snapshot and check for equality
    chain.load_snapshot()

    (
        check_eth_on_chain,
        check_base_on_chain,
    ) = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
    check_agent_wallet = hyperdrive_agent.wallet
    check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
    check_pool_info_on_chain = interactive_hyperdrive.interface.get_hyperdrive_state().pool_info
    check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

    assert check_eth_on_chain == init_eth_on_chain
    assert check_base_on_chain == init_base_on_chain
    assert check_agent_wallet == init_agent_wallet
    assert check_db_wallet.equals(init_db_wallet)
    assert check_pool_info_on_chain == init_pool_info_on_chain
    assert check_pool_state_on_db.equals(init_pool_state_on_db)


@pytest.mark.anvil
def test_set_variable_rate(chain: ILocalChain):
    """Set the variable rate."""
    # We need the underlying hyperdrive interface here to test time
    config = ILocalHyperdrive.Config(initial_variable_rate=FixedPoint("0.05"))
    interactive_hyperdrive = ILocalHyperdrive(chain, config)

    # Make a trade to mine the block on this variable rate so it shows up in the data pipeline
    _ = interactive_hyperdrive.init_agent()

    # Set the variable rate
    # This mines a block since it's a transaction
    interactive_hyperdrive.set_variable_rate(FixedPoint("0.10"))

    # Ensure variable rate has changed
    pool_state_df = interactive_hyperdrive.get_pool_state(coerce_float=False)

    assert pool_state_df["variable_rate"].iloc[0] == Decimal("0.05")
    assert pool_state_df["variable_rate"].iloc[-1] == Decimal("0.10")


@pytest.mark.anvil
def test_access_deployer_account(chain: ILocalChain):
    """Access the deployer account."""
    config = ILocalHyperdrive.Config(
        initial_liquidity=FixedPoint("100"),
    )
    interactive_hyperdrive = ILocalHyperdrive(chain, config)
    privkey = chain.get_deployer_account_private_key()  # anvil account 0
    pubkey = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    larry = interactive_hyperdrive.init_agent(base=FixedPoint(100_000), name="larry", private_key=privkey)
    larry_pubkey = larry.wallet.address.hex().strip("0x").lower()
    assert larry_pubkey == pubkey.lower().strip("0x")  # deployer public key


@pytest.mark.anvil
def test_access_deployer_liquidity(chain: ILocalChain):
    """Remove liquidity from the deployer account."""
    config = ILocalHyperdrive.Config(
        initial_liquidity=FixedPoint(100),
    )
    interactive_hyperdrive = ILocalHyperdrive(chain, config)
    privkey = chain.get_deployer_account_private_key()  # anvil account 0
    larry = interactive_hyperdrive.init_agent(base=FixedPoint(100_000), name="larry", private_key=privkey)
    assert (
        FixedPoint(
            scaled_value=interactive_hyperdrive.interface.hyperdrive_contract.functions.balanceOf(
                encode_asset_id(AssetIdPrefix.LP, 0),
                larry.checksum_address,
            ).call()
        )
        == larry.wallet.lp_tokens
    )
    # Hyperdrive pool steals 2 * minimumShareReserves from the initial deployer's liquidity
    assert larry.wallet.lp_tokens == config.initial_liquidity - 2 * config.minimum_share_reserves


@pytest.mark.anvil
def test_remove_deployer_liquidity(chain: ILocalChain):
    """Remove liquidity from the deployer account."""
    config = ILocalHyperdrive.Config(
        initial_liquidity=FixedPoint(100),
    )
    interactive_hyperdrive = ILocalHyperdrive(chain, config)
    privkey = chain.get_deployer_account_private_key()  # anvil account 0
    larry = interactive_hyperdrive.init_agent(base=FixedPoint(100_000), name="larry", private_key=privkey)
    larry.remove_liquidity(shares=larry.wallet.lp_tokens)
    assert larry.wallet.lp_tokens == 0
    assert (
        FixedPoint(
            scaled_value=interactive_hyperdrive.interface.hyperdrive_contract.functions.balanceOf(
                encode_asset_id(AssetIdPrefix.LP, 0),
                larry.checksum_address,
            ).call()
        )
        == 0
    )


@pytest.mark.anvil
def test_get_config_no_transactions(chain: ILocalChain):
    """Get pool config before executing any transactions."""
    interactive_hyperdrive = ILocalHyperdrive(chain)
    pool_config = interactive_hyperdrive.get_pool_config()
    assert isinstance(pool_config, Series)


@pytest.mark.anvil
def test_get_config_with_transactions(chain: ILocalChain):
    """Get pool config after executing one transaction."""
    interactive_hyperdrive = ILocalHyperdrive(chain)
    agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(100_000), eth=FixedPoint(100), name="alice")
    agent0.open_long(base=FixedPoint(11_111))
    pool_config = interactive_hyperdrive.get_pool_config()
    assert isinstance(pool_config, Series)


@pytest.mark.anvil
def test_liquidate(chain: ILocalChain):
    """Test liquidation."""
    interactive_hyperdrive = ILocalHyperdrive(chain)
    alice = interactive_hyperdrive.init_agent(base=FixedPoint(10_000), name="alice")
    alice.open_long(base=FixedPoint(100))
    alice.open_short(bonds=FixedPoint(100))
    alice.add_liquidity(base=FixedPoint(100))
    current_wallet = interactive_hyperdrive.get_current_wallet()
    assert current_wallet.shape[0] == 4  # we have 4 open positions, including base
    alice.liquidate()
    current_wallet = interactive_hyperdrive.get_current_wallet()
    assert current_wallet.shape[0] == 1  # we have 1 open position, including base


@pytest.mark.anvil
def test_random_liquidate(chain: ILocalChain):
    """Test random liquidation."""
    # Explicitly setting a random seed to remove randomness in the test
    interactive_config = ILocalHyperdrive.Config(rng_seed=1234)
    interactive_hyperdrive = ILocalHyperdrive(chain, interactive_config)
    alice = interactive_hyperdrive.init_agent(base=FixedPoint(10_000), name="alice")

    # We run the same trades 5 times, and ensure there's at least one difference
    # between the 5 liquidations.
    all_liquidate_events = []
    for _ in range(5):
        alice.open_long(base=FixedPoint(100))
        alice.open_short(bonds=FixedPoint(100))
        alice.add_liquidity(base=FixedPoint(100))
        current_wallet = interactive_hyperdrive.get_current_wallet()
        assert current_wallet.shape[0] == 4  # we have 4 open positions, including base
        liquidate_events = alice.liquidate(randomize=True)
        # We run liquidate here twice, as there's a chance the trades result in gaining withdrawal shares
        # TODO write loop within liquidate to call this multiple times
        # and also account for when no withdrawal shares are available to withdraw.
        liquidate_events.extend(alice.liquidate(randomize=True))
        current_wallet = interactive_hyperdrive.get_current_wallet()
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
def test_share_price_compounding_quincunx(chain: ILocalChain):
    """Share price when compounding by quincunx (one fifth of a year) should increase by more than the APR."""
    # setup
    initial_variable_rate = FixedPoint("0.045")
    interactive_config = ILocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0),
        curve_fee=FixedPoint(0),
        flat_fee=FixedPoint(0),
        initial_variable_rate=initial_variable_rate,
    )
    interactive_hyperdrive = ILocalHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    logging.info(f"Variable rate: {hyperdrive_interface.current_pool_state.variable_rate}")
    logging.info(f"Starting share price: {hyperdrive_interface.current_pool_state.pool_info.lp_share_price}")
    number_of_compounding_periods = 5
    for _ in range(number_of_compounding_periods):
        chain.advance_time(YEAR_IN_SECONDS // number_of_compounding_periods, create_checkpoints=False)
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
def test_share_price_compounding_annus(chain: ILocalChain):
    """Share price when compounding by annus (one year) should increase by exactly the APR (no compounding)."""
    # setup
    initial_variable_rate = FixedPoint("0.045")
    interactive_config = ILocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0),
        curve_fee=FixedPoint(0),
        flat_fee=FixedPoint(0),
        initial_variable_rate=initial_variable_rate,
    )
    interactive_hyperdrive = ILocalHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    logging.info(f"Variable rate: {hyperdrive_interface.current_pool_state.variable_rate}")
    logging.info(f"Starting share price: {hyperdrive_interface.current_pool_state.pool_info.lp_share_price}")
    chain.advance_time(YEAR_IN_SECONDS, create_checkpoints=False)
    ending_share_price = hyperdrive_interface.current_pool_state.pool_info.lp_share_price
    logging.info(f"Ending   share price: {ending_share_price}")
    assert ending_share_price - 1 == initial_variable_rate
