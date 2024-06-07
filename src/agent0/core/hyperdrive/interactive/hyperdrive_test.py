"""Tests interactive hyperdrive end to end."""

import pytest
from fixedpointmath import FixedPoint

from agent0.core.base.make_key import make_private_key
from agent0.ethpy.base.errors import ContractCallException
from agent0.ethpy.hyperdrive import AssetIdPrefix, encode_asset_id

from .chain import Chain
from .hyperdrive import Hyperdrive
from .hyperdrive_agent import HyperdriveAgent
from .local_chain import LocalChain
from .local_hyperdrive import LocalHyperdrive

# needed to pass in fixtures
# pylint: disable=redefined-outer-name
# ruff: noqa: PLR2004 (comparison against magic values (literals like numbers))
# allow non-lazy logging
# pylint: disable=logging-fstring-interpolation


def _ensure_db_wallet_matches_agent_wallet_and_chain(in_hyperdrive: Hyperdrive, agent: HyperdriveAgent):
    # pylint: disable=too-many-locals

    # NOTE this function is assuming only one agent is making trades
    interface = in_hyperdrive.interface

    # Test against db
    positions_df = agent.get_positions(coerce_float=False, pool_filter=in_hyperdrive)
    # Filter for wallet
    positions_df = positions_df[positions_df["wallet_address"] == agent.address]

    agent_wallet = agent.get_wallet()

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


@pytest.mark.anvil
def test_hyperdrive_from_local_chain_not_allowed(fast_chain_fixture: LocalChain):
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 365,  # 1 year
    )
    # Launches a local hyperdrive pool
    # This deploys the pool
    interactive_local_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)

    hyperdrive_address = interactive_local_hyperdrive.hyperdrive_address
    with pytest.raises(TypeError):
        # We ensure we can't initialize a remote hyperdrive object from a local chain.
        _ = Hyperdrive(fast_chain_fixture, hyperdrive_address)


# Lots of things to test
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# ruff: noqa: PLR0915 (too many statements)
@pytest.mark.anvil
def test_remote_funding_and_trades(fast_chain_fixture: LocalChain):
    """Deploy a local chain and point the remote interface to the local chain."""
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 365,  # 1 year
    )
    # Launches a local hyperdrive pool
    # This deploys the pool
    interactive_local_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)

    # Gather relevant objects from the local hyperdrive
    hyperdrive_address = interactive_local_hyperdrive.hyperdrive_address

    # Connect to the local chain using the remote hyperdrive interface
    # To avoid a port conflict with the existing db container in `fast_chain_fixture`,
    # we use a separate chain port here
    remote_chain = Chain(fast_chain_fixture.rpc_uri, Chain.Config(db_port=40000))
    interactive_remote_hyperdrive = Hyperdrive(remote_chain, hyperdrive_address)

    # Generate trading agents from the interactive object
    hyperdrive_agent0 = remote_chain.init_agent(private_key=make_private_key(), pool=interactive_remote_hyperdrive)
    hyperdrive_agent1 = remote_chain.init_agent(private_key=make_private_key(), pool=interactive_remote_hyperdrive)

    # Add funds
    hyperdrive_agent0.add_funds(base=FixedPoint(1_111_111), eth=FixedPoint(111))
    hyperdrive_agent1.add_funds(base=FixedPoint(222_222), eth=FixedPoint(222))

    # Set max approval
    hyperdrive_agent0.set_max_approval()
    hyperdrive_agent1.set_max_approval()

    # Ensure agent wallet have expected balances
    assert (hyperdrive_agent0.get_wallet().balance.amount) == FixedPoint(1_111_111)
    assert (hyperdrive_agent1.get_wallet().balance.amount) == FixedPoint(222_222)

    # Ensure chain balances are as expected
    (
        chain_eth_balance,
        chain_base_balance,
    ) = interactive_remote_hyperdrive.interface.get_eth_base_balances(hyperdrive_agent0.account)
    assert chain_base_balance == FixedPoint(1_111_111)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    # This epsilon is a bit bigger than i_local_hyperdrive_test because we use this account
    # for approval in the remote case, whereas we use the deployer account in the local case.
    assert (FixedPoint(111) - chain_eth_balance) < FixedPoint("0.0002")
    (
        chain_eth_balance,
        chain_base_balance,
    ) = interactive_remote_hyperdrive.interface.get_eth_base_balances(hyperdrive_agent1.account)
    assert chain_base_balance == FixedPoint(222_222)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    assert (FixedPoint(222) - chain_eth_balance) < FixedPoint("0.0002")

    # Test trades
    add_liquidity_event = hyperdrive_agent0.add_liquidity(base=FixedPoint(111_111))
    assert add_liquidity_event.as_base
    assert add_liquidity_event.amount == FixedPoint(111_111)
    assert hyperdrive_agent0.get_wallet().lp_tokens == add_liquidity_event.lp_amount
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # Open long
    open_long_event = hyperdrive_agent0.open_long(base=FixedPoint(22_222))
    assert open_long_event.as_base
    assert open_long_event.amount == FixedPoint(22_222)
    agent0_longs = list(hyperdrive_agent0.get_wallet().longs.values())
    assert len(agent0_longs) == 1
    assert agent0_longs[0].balance == open_long_event.bond_amount
    assert agent0_longs[0].maturity_time == open_long_event.maturity_time
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # Testing adding another agent to the pool after trades have been made, making a trade,
    # then checking wallet
    hyperdrive_agent2 = remote_chain.init_agent(private_key=make_private_key(), pool=interactive_remote_hyperdrive)
    hyperdrive_agent2.add_funds(base=FixedPoint(111_111), eth=FixedPoint(111))
    hyperdrive_agent2.set_max_approval()
    open_long_event_2 = hyperdrive_agent2.open_long(base=FixedPoint(333))

    assert open_long_event_2.as_base
    assert open_long_event_2.amount == FixedPoint(333)
    agent2_longs = list(hyperdrive_agent2.get_wallet().longs.values())
    assert len(agent2_longs) == 1
    assert agent2_longs[0].balance == open_long_event_2.bond_amount
    assert agent2_longs[0].maturity_time == open_long_event_2.maturity_time
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # Remove liquidity
    remove_liquidity_event = hyperdrive_agent0.remove_liquidity(shares=add_liquidity_event.lp_amount)
    assert add_liquidity_event.lp_amount == remove_liquidity_event.lp_amount
    assert hyperdrive_agent0.get_wallet().lp_tokens == FixedPoint(0)
    assert hyperdrive_agent0.get_wallet().withdraw_shares == remove_liquidity_event.withdrawal_share_amount
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # We ensure there exists some withdrawal shares that were given from the previous trade for testing purposes
    assert remove_liquidity_event.withdrawal_share_amount > 0

    # Add liquidity back to ensure we can close positions
    add_liquidity_event = hyperdrive_agent0.add_liquidity(base=FixedPoint(111_111))
    assert add_liquidity_event.as_base
    assert add_liquidity_event.amount == FixedPoint(111_111)
    assert hyperdrive_agent0.get_wallet().lp_tokens == add_liquidity_event.lp_amount
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # Open short
    open_short_event = hyperdrive_agent0.open_short(bonds=FixedPoint(333))
    assert open_short_event.bond_amount == FixedPoint(333)
    agent0_shorts = list(hyperdrive_agent0.get_wallet().shorts.values())
    assert len(agent0_shorts) == 1
    assert agent0_shorts[0].balance == open_short_event.bond_amount
    assert agent0_shorts[0].maturity_time == open_short_event.maturity_time
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # Close long
    close_long_event = hyperdrive_agent0.close_long(
        maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
    )
    assert open_long_event.bond_amount == close_long_event.bond_amount
    assert open_long_event.maturity_time == close_long_event.maturity_time
    assert len(hyperdrive_agent0.get_wallet().longs) == 0
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # Close short
    close_short_event = hyperdrive_agent0.close_short(
        maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
    )
    assert open_short_event.bond_amount == close_short_event.bond_amount
    assert open_short_event.maturity_time == close_short_event.maturity_time
    assert len(hyperdrive_agent0.get_wallet().shorts) == 0
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    # Redeem withdrawal shares
    # Note that redeeming withdrawal shares for more than available in the pool
    # will pull out as much withdrawal shares as possible
    redeem_event = hyperdrive_agent0.redeem_withdrawal_share(shares=remove_liquidity_event.withdrawal_share_amount)
    assert (
        hyperdrive_agent0.get_wallet().withdraw_shares
        == remove_liquidity_event.withdrawal_share_amount - redeem_event.withdrawal_share_amount
    )
    _ensure_db_wallet_matches_agent_wallet_and_chain(interactive_remote_hyperdrive, hyperdrive_agent0)

    remote_chain.cleanup()


@pytest.mark.anvil
def test_no_policy_call(fast_chain_fixture: LocalChain):
    """Test no policy call error on the base remote chain."""
    initial_pool_config = LocalHyperdrive.Config()
    interactive_local_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)
    hyperdrive_addresses = interactive_local_hyperdrive.hyperdrive_address
    # Connect to the local chain using the remote hyperdrive interface
    # To avoid a port conflict with the existing db container in `fast_chain_fixture`,
    # we use a separate chain port here
    remote_chain = Chain(fast_chain_fixture.rpc_uri, Chain.Config(db_port=40000))
    interactive_remote_hyperdrive = Hyperdrive(remote_chain, hyperdrive_addresses)

    # Create agent without policy passed in
    hyperdrive_agent = remote_chain.init_agent(private_key=make_private_key(), pool=interactive_remote_hyperdrive)
    # Attempt to execute agent policy, should throw value error
    with pytest.raises(ValueError):
        hyperdrive_agent.execute_policy_action()

    remote_chain.cleanup()


@pytest.mark.anvil
def test_no_approval(fast_chain_fixture: LocalChain):
    """Test no approval error on the base remote chain."""
    initial_pool_config = LocalHyperdrive.Config()
    local_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)
    private_key = make_private_key()

    # Initialize the agent here to fund
    fast_chain_fixture.init_agent(
        base=FixedPoint(1_000_000), eth=FixedPoint(1_000), private_key=private_key, pool=local_hyperdrive
    )
    hyperdrive_addresses = local_hyperdrive.hyperdrive_address
    # Connect to the local chain using the remote hyperdrive interface
    # To avoid a port conflict with the existing db container in `fast_chain_fixture`,
    # we use a separate chain port here

    remote_chain = Chain(
        fast_chain_fixture.rpc_uri,
        Chain.Config(
            db_port=40000,
        ),
    )
    interactive_remote_hyperdrive = Hyperdrive(remote_chain, hyperdrive_addresses)
    # Create agent with same private key
    hyperdrive_agent = remote_chain.init_agent(private_key=private_key, pool=interactive_remote_hyperdrive)

    # Make a call without approval
    try:
        hyperdrive_agent.add_liquidity(base=FixedPoint(1_000))
    except ContractCallException as exc:
        assert "Insufficient allowance: " in exc.args[0]

    try:
        hyperdrive_agent.open_long(base=FixedPoint(1_000))
    except ContractCallException as exc:
        assert "Insufficient allowance: " in exc.args[0]

    try:
        hyperdrive_agent.open_short(bonds=FixedPoint(1_000))
    except ContractCallException as exc:
        assert "Insufficient allowance: " in exc.args[0]

    remote_chain.cleanup()


@pytest.mark.anvil
def test_out_of_gas(fast_chain_fixture: LocalChain):
    """Test out of gas error on the base remote chain."""
    initial_pool_config = LocalHyperdrive.Config()
    local_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)
    private_key = make_private_key()

    # Initialize the agent here to fund
    fast_chain_fixture.init_agent(
        base=FixedPoint(1_000_000), eth=FixedPoint(1_000), private_key=private_key, pool=local_hyperdrive
    )
    hyperdrive_addresses = local_hyperdrive.hyperdrive_address
    # Connect to the local chain using the remote hyperdrive interface
    # To avoid a port conflict with the existing db container in `fast_chain_fixture`,
    # we use a separate chain port here

    remote_chain = Chain(
        fast_chain_fixture.rpc_uri,
        Chain.Config(
            db_port=40000,
            gas_limit=100000,
        ),
    )
    interactive_remote_hyperdrive = Hyperdrive(remote_chain, hyperdrive_addresses)
    # Create agent with same private key
    hyperdrive_agent = remote_chain.init_agent(private_key=private_key, pool=interactive_remote_hyperdrive)
    hyperdrive_agent.set_max_approval()

    # Make a call with not enough gas
    try:
        hyperdrive_agent.add_liquidity(base=FixedPoint(1_000))
    except ContractCallException as exc:
        assert "Out of gas" in exc.args[0]

    remote_chain.cleanup()
