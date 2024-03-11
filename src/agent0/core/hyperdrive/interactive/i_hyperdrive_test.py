"""Tests interactive hyperdrive end to end."""

import pytest
from fixedpointmath import FixedPoint

from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive import HyperdriveWallet
from agent0.ethpy.hyperdrive import AssetIdPrefix, HyperdriveReadInterface, encode_asset_id

from .i_chain import IChain
from .i_hyperdrive import IHyperdrive
from .i_local_chain import ILocalChain
from .i_local_hyperdrive import ILocalHyperdrive

# needed to pass in fixtures
# pylint: disable=redefined-outer-name
# ruff: noqa: PLR2004 (comparison against magic values (literals like numbers))
# allow non-lazy logging
# pylint: disable=logging-fstring-interpolation


def _ensure_agent_wallet_is_correct(wallet: HyperdriveWallet, interface: HyperdriveReadInterface) -> None:
    """Check that the agent's wallet matches what's reported from the chain.

    Will assert that balances match.

    Arguments
    ---------
    wallet: HyperdriveWallet
        The HyperdriveWallet object to check against the chain
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object
    """
    # Check base
    base_from_chain = interface.base_token_contract.functions.balanceOf(
        interface.web3.to_checksum_address(wallet.address.hex())
    ).call()
    assert wallet.balance.amount == FixedPoint(scaled_value=base_from_chain)

    # Check lp positions
    asset_id = encode_asset_id(AssetIdPrefix.LP, 0)
    address = interface.web3.to_checksum_address(wallet.address.hex())
    lp_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
    assert wallet.lp_tokens == FixedPoint(scaled_value=lp_from_chain)

    # Check withdrawal positions
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    address = interface.web3.to_checksum_address(wallet.address.hex())
    withdrawal_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
    assert wallet.withdraw_shares == FixedPoint(scaled_value=withdrawal_from_chain)

    # Check long positions
    for long_time, long_amount in wallet.longs.items():
        asset_id = encode_asset_id(AssetIdPrefix.LONG, long_time)
        address = interface.web3.to_checksum_address(wallet.address.hex())
        long_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
        assert long_amount.balance == FixedPoint(scaled_value=long_from_chain)

    # Check short positions
    for short_time, short_amount in wallet.shorts.items():
        asset_id = encode_asset_id(AssetIdPrefix.SHORT, short_time)
        address = interface.web3.to_checksum_address(wallet.address.hex())
        short_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
        assert short_amount.balance == FixedPoint(scaled_value=short_from_chain)


# Lots of things to test
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# ruff: noqa: PLR0915 (too many statements)
@pytest.mark.anvil
@pytest.mark.parametrize("check_remote_chain", [True, False])
def test_remote_funding_and_trades(chain: ILocalChain, check_remote_chain: bool):
    """Deploy a local chain and point the remote interface to the local chain."""
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = ILocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 365,  # 1 year
    )
    # Launches a local hyperdrive pool
    # This deploys the pool
    interactive_local_hyperdrive = ILocalHyperdrive(chain, initial_pool_config)

    # Gather relevant objects from the local hyperdrive
    hyperdrive_addresses = interactive_local_hyperdrive.get_hyperdrive_addresses()

    # Connect to the local chain using the remote hyperdrive interface
    if check_remote_chain:
        remote_chain = IChain(chain.rpc_uri)
        interactive_remote_hyperdrive = IHyperdrive(remote_chain, hyperdrive_addresses)
    else:
        interactive_remote_hyperdrive = IHyperdrive(chain, hyperdrive_addresses)

    # Generate trading agents from the interactive object
    hyperdrive_agent0 = interactive_remote_hyperdrive.init_agent(private_key=make_private_key())
    hyperdrive_agent1 = interactive_remote_hyperdrive.init_agent(private_key=make_private_key())

    # Add funds
    hyperdrive_agent0.add_funds(base=FixedPoint(1_111_111), eth=FixedPoint(111))
    hyperdrive_agent1.add_funds(base=FixedPoint(222_222), eth=FixedPoint(222))

    # Set max approval
    hyperdrive_agent0.set_max_approval()
    hyperdrive_agent1.set_max_approval()

    # Ensure agent wallet have expected balances
    assert (hyperdrive_agent0.wallet.balance.amount) == FixedPoint(1_111_111)
    assert (hyperdrive_agent1.wallet.balance.amount) == FixedPoint(222_222)

    # Ensure chain balances are as expected
    (
        chain_eth_balance,
        chain_base_balance,
    ) = interactive_remote_hyperdrive.interface.get_eth_base_balances(hyperdrive_agent0.agent)
    assert chain_base_balance == FixedPoint(1_111_111)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    # This epsilon is a bit bigger than i_local_hyperdrive_test because we use this account
    # for approval in the remote case, whereas we use the deployer account in the local case.
    assert (FixedPoint(111) - chain_eth_balance) < FixedPoint("0.0002")
    (
        chain_eth_balance,
        chain_base_balance,
    ) = interactive_remote_hyperdrive.interface.get_eth_base_balances(hyperdrive_agent1.agent)
    assert chain_base_balance == FixedPoint(222_222)
    # There was a little bit of gas spent to approve, so we don't do a direct comparison here
    assert (FixedPoint(222) - chain_eth_balance) < FixedPoint("0.0002")

    # Test trades
    add_liquidity_event = hyperdrive_agent0.add_liquidity(base=FixedPoint(111_111))
    assert add_liquidity_event.base_amount == FixedPoint(111_111)
    assert hyperdrive_agent0.wallet.lp_tokens == add_liquidity_event.lp_amount
    _ensure_agent_wallet_is_correct(hyperdrive_agent0.wallet, interactive_remote_hyperdrive.interface)

    # Open long
    open_long_event = hyperdrive_agent0.open_long(base=FixedPoint(22_222))
    assert open_long_event.base_amount == FixedPoint(22_222)
    agent0_longs = list(hyperdrive_agent0.wallet.longs.values())
    assert len(agent0_longs) == 1
    assert agent0_longs[0].balance == open_long_event.bond_amount
    assert agent0_longs[0].maturity_time == open_long_event.maturity_time
    _ensure_agent_wallet_is_correct(hyperdrive_agent0.wallet, interactive_remote_hyperdrive.interface)

    # Testing adding another agent to the pool after trades have been made, making a trade,
    # then checking wallet
    hyperdrive_agent2 = interactive_remote_hyperdrive.init_agent(private_key=make_private_key())
    hyperdrive_agent2.add_funds(base=FixedPoint(111_111), eth=FixedPoint(111))
    hyperdrive_agent2.set_max_approval()
    open_long_event_2 = hyperdrive_agent2.open_long(base=FixedPoint(333))

    assert open_long_event_2.base_amount == FixedPoint(333)
    agent2_longs = list(hyperdrive_agent2.wallet.longs.values())
    assert len(agent2_longs) == 1
    assert agent2_longs[0].balance == open_long_event_2.bond_amount
    assert agent2_longs[0].maturity_time == open_long_event_2.maturity_time
    _ensure_agent_wallet_is_correct(hyperdrive_agent2.wallet, interactive_remote_hyperdrive.interface)

    # Remove liquidity
    remove_liquidity_event = hyperdrive_agent0.remove_liquidity(shares=add_liquidity_event.lp_amount)
    assert add_liquidity_event.lp_amount == remove_liquidity_event.lp_amount
    assert hyperdrive_agent0.wallet.lp_tokens == FixedPoint(0)
    assert hyperdrive_agent0.wallet.withdraw_shares == remove_liquidity_event.withdrawal_share_amount
    _ensure_agent_wallet_is_correct(hyperdrive_agent0.wallet, interactive_remote_hyperdrive.interface)

    # We ensure there exists some withdrawal shares that were given from the previous trade for testing purposes
    assert remove_liquidity_event.withdrawal_share_amount > 0

    # Open short
    open_short_event = hyperdrive_agent0.open_short(bonds=FixedPoint(333))
    assert open_short_event.bond_amount == FixedPoint(333)
    agent0_shorts = list(hyperdrive_agent0.wallet.shorts.values())
    assert len(agent0_shorts) == 1
    assert agent0_shorts[0].balance == open_short_event.bond_amount
    assert agent0_shorts[0].maturity_time == open_short_event.maturity_time
    _ensure_agent_wallet_is_correct(hyperdrive_agent0.wallet, interactive_remote_hyperdrive.interface)

    # Close long
    close_long_event = hyperdrive_agent0.close_long(
        maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
    )
    assert open_long_event.bond_amount == close_long_event.bond_amount
    assert open_long_event.maturity_time == close_long_event.maturity_time
    assert len(hyperdrive_agent0.wallet.longs) == 0
    _ensure_agent_wallet_is_correct(hyperdrive_agent0.wallet, interactive_remote_hyperdrive.interface)

    # Close short
    close_short_event = hyperdrive_agent0.close_short(
        maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
    )
    assert open_short_event.bond_amount == close_short_event.bond_amount
    assert open_short_event.maturity_time == close_short_event.maturity_time
    assert len(hyperdrive_agent0.wallet.shorts) == 0
    _ensure_agent_wallet_is_correct(hyperdrive_agent0.wallet, interactive_remote_hyperdrive.interface)

    # Redeem withdrawal shares
    # Note that redeeming withdrawal shares for more than available in the pool
    # will pull out as much withdrawal shares as possible
    redeem_event = hyperdrive_agent0.redeem_withdraw_share(shares=remove_liquidity_event.withdrawal_share_amount)
    assert (
        hyperdrive_agent0.wallet.withdraw_shares
        == remove_liquidity_event.withdrawal_share_amount - redeem_event.withdrawal_share_amount
    )
    _ensure_agent_wallet_is_correct(hyperdrive_agent0.wallet, interactive_remote_hyperdrive.interface)


@pytest.mark.anvil
@pytest.mark.parametrize("check_remote_chain", [True, False])
def test_multi_account_bookkeeping(chain: ILocalChain, check_remote_chain: bool):
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = ILocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 365,  # 1 year
    )
    # Launches a local hyperdrive pool
    # This deploys the pool
    interactive_local_hyperdrive_0 = ILocalHyperdrive(chain, initial_pool_config)
    interactive_local_hyperdrive_1 = ILocalHyperdrive(chain, initial_pool_config)

    # Gather relevant objects from the local hyperdrive
    hyperdrive_addresses_0 = interactive_local_hyperdrive_0.get_hyperdrive_addresses()
    hyperdrive_addresses_1 = interactive_local_hyperdrive_1.get_hyperdrive_addresses()

    # Connect to the local chain using the remote hyperdrive interface
    if check_remote_chain:
        remote_chain = IChain(chain.rpc_uri)
        interactive_remote_hyperdrive_0 = IHyperdrive(remote_chain, hyperdrive_addresses_0)
        interactive_remote_hyperdrive_1 = IHyperdrive(remote_chain, hyperdrive_addresses_1)
    else:
        interactive_remote_hyperdrive_0 = IHyperdrive(chain, hyperdrive_addresses_0)
        interactive_remote_hyperdrive_1 = IHyperdrive(chain, hyperdrive_addresses_1)

    # Generate trading agents from the interactive object
    private_key = make_private_key()
    _ = interactive_remote_hyperdrive_0.init_agent(private_key=private_key)

    # Initializing an agent with an existing key should fail
    with pytest.raises(ValueError):
        _ = interactive_remote_hyperdrive_0.init_agent(private_key=private_key)

    # Initializing an agent with an existing key on a separate pool should fail
    with pytest.raises(ValueError):
        _ = interactive_remote_hyperdrive_1.init_agent(private_key=private_key)
