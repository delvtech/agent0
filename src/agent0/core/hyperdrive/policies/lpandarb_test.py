"""Test the ability of bots to hit a target rate."""

from __future__ import annotations

import logging

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.interactive.event_types import AddLiquidity, CloseLong, CloseShort, OpenLong, OpenShort
from agent0.core.hyperdrive.interactive.local_hyperdrive_agent import LocalHyperdriveAgent
from agent0.core.hyperdrive.policies import PolicyZoo

# avoid unnecessary warning from using fixtures defined in outer scope
# pylint: disable=redefined-outer-name

TRADE_AMOUNTS = [0.003, 1e7]  # 0.003 is three times the minimum transaction amount of local test deploy
# We hit the target rate to the 4th decimal of precision.
# That means 0.05001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-4)
YEAR_IN_SECONDS = 31_536_000

# pylint: disable=missing-function-docstring,too-many-statements,logging-fstring-interpolation,missing-return-type-doc
# pylint: disable=missing-return-doc,too-many-function-args


# TODO use the existing fixtures instead of custom fixture here
@pytest.fixture(scope="function")
def interactive_hyperdrive(fast_chain_fixture: LocalChain) -> LocalHyperdrive:
    """Create interactive hyperdrive.

    Arguments
    ---------
    fast_chain_fixture: LocalChain
        Local chain fixture.

    Returns
    -------
    InteractiveHyperdrive
        Interactive hyperdrive.
    """
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        initial_fixed_apr=FixedPoint("0.05"),
    )
    return LocalHyperdrive(fast_chain_fixture, interactive_config)


@pytest.fixture(scope="function")
def arbitrage_andy(interactive_hyperdrive: LocalHyperdrive) -> LocalHyperdriveAgent:
    """Create Arbitrage Andy interactive hyperdrive agent used to arbitrage the fixed rate to the variable rate.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.

    Returns
    -------
    InteractiveHyperdriveAgent
        Arbitrage Andy interactive hyperdrive agent.
    """
    return create_arbitrage_andy(interactive_hyperdrive)


def create_arbitrage_andy(interactive_hyperdrive: LocalHyperdrive) -> LocalHyperdriveAgent:
    """Create Arbitrage Andy interactive hyperdrive agent used to arbitrage the fixed rate to the variable rate.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.

    Returns
    -------
    InteractiveHyperdriveAgent
        Arbitrage Andy interactive hyperdrive agent.
    """
    andy_base = FixedPoint(1e9)
    andy_config = PolicyZoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        min_trade_amount_bonds=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    return interactive_hyperdrive.chain.init_agent(
        base=andy_base,
        eth=FixedPoint(10),
        name="andy",
        pool=interactive_hyperdrive,
        policy=PolicyZoo.lp_and_arb,
        policy_config=andy_config,
    )


@pytest.fixture(scope="function")
def manual_agent(interactive_hyperdrive: LocalHyperdrive) -> LocalHyperdriveAgent:
    """Create manual interactive hyperdrive agent used to manually move markets.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.

    Returns
    -------
    InteractiveHyperdriveAgent
        Manual interactive hyperdrive agent.
    """
    return interactive_hyperdrive.chain.init_agent(
        base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive
    )


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_long(
    interactive_hyperdrive: LocalHyperdrive,
    trade_amount: float,
    arbitrage_andy: LocalHyperdriveAgent,
    manual_agent: LocalHyperdriveAgent,
):
    """Open a long to hit the target rate."""
    # change the fixed rate
    manual_agent.open_short(bonds=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # arbitrage it back (the only trade capable of this is a long)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_spot_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    assert variable_rate is not None
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_short(
    interactive_hyperdrive: LocalHyperdrive,
    trade_amount: float,
    arbitrage_andy: LocalHyperdriveAgent,
    manual_agent: LocalHyperdriveAgent,
):
    """Open a short to hit the target rate."""
    # change the fixed rate
    manual_agent.open_long(base=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # arbitrage it back (the only trade capable of this is a short)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_spot_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    assert variable_rate is not None
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


# pylint: disable=too-many-locals
@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", [0.003, 10])
def test_close_long(
    interactive_hyperdrive: LocalHyperdrive,
    trade_amount: float,
    arbitrage_andy: LocalHyperdriveAgent,
    manual_agent: LocalHyperdriveAgent,
):
    """Close a long to hit the target rate."""
    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # give andy a long position twice the trade amount, to be sufficiently large when closing
    pool_bonds_before = interactive_hyperdrive.interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.interface.current_pool_state.block_time
    event = arbitrage_andy.open_long(base=FixedPoint(3 * trade_amount))
    pool_bonds_after = interactive_hyperdrive.interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.interface.current_pool_state.block_time
    d_bonds = pool_bonds_after - pool_bonds_before  # instead of event.bond_amount
    d_shares = pool_shares_after - pool_shares_before  # instead of event.amount
    d_time = block_time_after - block_time_before
    logging.info("Andy opened long %s base.", 3 * trade_amount)
    logging.info("Δtime=%s", d_time)
    logging.info(
        " pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares
    )
    assert event.as_base
    logging.info(
        " event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.amount > 0 else "",
        event.amount,
    )
    # undo this trade manually
    event = manual_agent.open_short(bonds=FixedPoint(event.bond_amount * FixedPoint(1.006075)))
    assert event.as_base
    logging.info(
        "manually opened short. event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.amount > 0 else "",
        event.amount,
    )

    # report fixed rate
    logging.info("fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # change the fixed rate
    event = manual_agent.open_long(base=FixedPoint(trade_amount))
    assert event.as_base
    logging.info(
        "manually opened short. event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.amount > 0 else "",
        event.amount,
    )
    # report fixed rate
    logging.info("fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # arbitrage it all back in one trade
    pool_bonds_before = interactive_hyperdrive.interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.interface.current_pool_state.block_time
    event_list = arbitrage_andy.execute_policy_action()
    logging.info("Andy executed %s", event_list)
    event = event_list[0] if isinstance(event_list, list) else event_list
    assert isinstance(event, CloseLong)
    pool_bonds_after = interactive_hyperdrive.interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.interface.current_pool_state.block_time
    d_bonds = pool_bonds_after - pool_bonds_before  # instead of event.bond_amount
    d_shares = pool_shares_after - pool_shares_before  # instead of event.amount
    d_time = block_time_after - block_time_before
    assert event.as_base
    logging.info("Andy closed long; amount determined by policy.")
    logging.info("Δtime=%s", d_time)
    logging.info(
        " pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares
    )
    logging.info(
        " event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.amount > 0 else "",
        event.amount,
    )

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_spot_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    assert variable_rate is not None
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
def test_already_at_target(interactive_hyperdrive: LocalHyperdrive, arbitrage_andy: LocalHyperdriveAgent):
    """Already at target, do nothing."""
    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # arbitrage it back
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_spot_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    assert variable_rate is not None
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
def test_reduce_long(interactive_hyperdrive: LocalHyperdrive, arbitrage_andy: LocalHyperdriveAgent):
    """Reduce a long position."""
    # give Andy a long
    event = arbitrage_andy.open_long(base=FixedPoint(10))

    # advance time to maturity
    interactive_hyperdrive.chain.advance_time(int(YEAR_IN_SECONDS / 2), create_checkpoints=False)

    # see if he reduces the long
    event = arbitrage_andy.execute_policy_action()
    event = event[0] if isinstance(event, list) else event
    logging.info("event is %s", event)
    assert isinstance(event, CloseLong)


@pytest.mark.anvil
def test_reduce_short(interactive_hyperdrive: LocalHyperdrive, arbitrage_andy: LocalHyperdriveAgent):
    """Reduce a short position."""
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # give Andy a short
    event = arbitrage_andy.open_short(bonds=FixedPoint(10))

    logging.info("fixed rate after open short is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # advance time to maturity
    interactive_hyperdrive.chain.advance_time(int(YEAR_IN_SECONDS / 2), create_checkpoints=False)

    # see if he reduces the short
    event = arbitrage_andy.execute_policy_action()
    event = event[0] if isinstance(event, list) else event
    logging.info("event is %s", event)
    assert isinstance(event, CloseShort)


@pytest.mark.anvil
def test_safe_long_trading(interactive_hyperdrive: LocalHyperdrive, manual_agent: LocalHyperdriveAgent):
    """Test that the agent doesn't overextend itself."""
    # setup
    larry_base = FixedPoint(1e4)
    larry_config = PolicyZoo.lp_and_arb.Config(
        lp_portion=FixedPoint("0.99"),
        min_trade_amount_bonds=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    larry = interactive_hyperdrive.chain.init_agent(
        base=larry_base,
        eth=FixedPoint(10),
        name="larry",
        pool=interactive_hyperdrive,
        policy=PolicyZoo.lp_and_arb,
        policy_config=larry_config,
    )
    # change the fixed rate
    manual_agent.open_short(bonds=FixedPoint(100_000))
    # lp & arb
    action_result = larry.execute_policy_action()  # should not be able to arb the full amount after LPing
    # checks
    assert len(action_result) == 2  # LP & Arb (no closing trades)
    assert isinstance(action_result[0], AddLiquidity)  # LP first
    assert isinstance(action_result[1], OpenLong)  # then arb


@pytest.mark.anvil
def test_safe_short_trading(interactive_hyperdrive: LocalHyperdrive, manual_agent: LocalHyperdriveAgent):
    """Test that the agent doesn't overextend itself."""
    # setup
    larry_base = FixedPoint(1e4)
    larry_config = PolicyZoo.lp_and_arb.Config(
        lp_portion=FixedPoint("0.9"),
        min_trade_amount_bonds=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    larry = interactive_hyperdrive.chain.init_agent(
        base=larry_base,
        eth=FixedPoint(10),
        name="larry",
        pool=interactive_hyperdrive,
        policy=PolicyZoo.lp_and_arb,
        policy_config=larry_config,
    )
    # change the fixed rate
    manual_agent.open_long(base=FixedPoint(100_000))
    # lp & arb
    action_result = larry.execute_policy_action()  # should not be able to arb the full amount after LPing
    # checks
    assert len(action_result) == 2  # LP & Arb (no closing trades)
    assert isinstance(action_result[0], AddLiquidity)  # LP first
    assert isinstance(action_result[1], OpenShort)  # then arb


@pytest.mark.anvil
def test_matured_long(interactive_hyperdrive: LocalHyperdrive, arbitrage_andy: LocalHyperdriveAgent):
    """Don't touch the matured long."""
    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # arbitrage it back
    arbitrage_andy.open_long(base=FixedPoint(100_000))

    interactive_hyperdrive.chain.advance_time(int(YEAR_IN_SECONDS * 2), create_checkpoints=False)

    # check Andy's trades to make sure he doesn't CloseLong
    event = arbitrage_andy.execute_policy_action()
    event = event[0] if isinstance(event, list) else event
    logging.info("event is %s", event)
    assert not isinstance(event, CloseLong)


@pytest.mark.anvil
def test_matured_short(interactive_hyperdrive: LocalHyperdrive, arbitrage_andy: LocalHyperdriveAgent):
    """Don't touch the matured short."""
    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_spot_rate())

    # arbitrage it back
    arbitrage_andy.open_short(bonds=FixedPoint(100_000))

    interactive_hyperdrive.chain.advance_time(int(YEAR_IN_SECONDS * 2), create_checkpoints=False)

    # check Andy's trades to make sure he doesn't CloseShort
    event = arbitrage_andy.execute_policy_action()
    event = event[0] if isinstance(event, list) else event
    logging.info("event is %s", event)
    assert not isinstance(event, CloseShort)
