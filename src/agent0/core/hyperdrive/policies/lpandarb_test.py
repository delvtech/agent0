"""Test the ability of bots to hit a target rate."""

from __future__ import annotations

import logging

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import ILocalChain, ILocalHyperdrive
from agent0.core.hyperdrive.interactive.event_types import AddLiquidity, CloseLong, CloseShort, OpenLong, OpenShort
from agent0.core.hyperdrive.interactive.i_local_hyperdrive_agent import ILocalHyperdriveAgent
from agent0.core.hyperdrive.policies import PolicyZoo

# avoid unnecessary warning from using fixtures defined in outer scope
# pylint: disable=redefined-outer-name

TRADE_AMOUNTS = [0.003, 1e7]  # 0.003 is three times the minimum transaction amount of local test deploy
# We hit the target rate to the 5th decimal of precision.
# That means 0.050001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-5)
YEAR_IN_SECONDS = 31_536_000

# pylint: disable=missing-function-docstring,too-many-statements,logging-fstring-interpolation,missing-return-type-doc
# pylint: disable=missing-return-doc,too-many-function-args


@pytest.fixture(scope="function")
def interactive_hyperdrive(chain: ILocalChain) -> ILocalHyperdrive:
    """Create interactive hyperdrive.

    Arguments
    ---------
    chain: LocalChain
        Local chain.

    Returns
    -------
    InteractiveHyperdrive
        Interactive hyperdrive."""
    interactive_config = ILocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        initial_fixed_apr=FixedPoint("0.05"),
    )
    return ILocalHyperdrive(chain, interactive_config)


@pytest.fixture(scope="function")
def arbitrage_andy(interactive_hyperdrive) -> ILocalHyperdriveAgent:
    """Create Arbitrage Andy interactive hyperdrive agent used to arbitrage the fixed rate to the variable rate.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.

    Returns
    -------
    InteractiveHyperdriveAgent
        Arbitrage Andy interactive hyperdrive agent."""
    return create_arbitrage_andy(interactive_hyperdrive)


def create_arbitrage_andy(interactive_hyperdrive) -> ILocalHyperdriveAgent:
    """Create Arbitrage Andy interactive hyperdrive agent used to arbitrage the fixed rate to the variable rate.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.

    Returns
    -------
    InteractiveHyperdriveAgent
        Arbitrage Andy interactive hyperdrive agent."""
    andy_base = FixedPoint(1e9)
    andy_config = PolicyZoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        min_trade_amount_bonds=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    return interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=PolicyZoo.lp_and_arb, policy_config=andy_config
    )


@pytest.fixture(scope="function")
def manual_agent(interactive_hyperdrive) -> ILocalHyperdriveAgent:
    """Create manual interactive hyperdrive agent used to manually move markets.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.

    Returns
    -------
    InteractiveHyperdriveAgent
        Manual interactive hyperdrive agent."""
    return interactive_hyperdrive.init_agent(base=FixedPoint(1e9))


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_long(
    interactive_hyperdrive: ILocalHyperdrive,
    trade_amount: float,
    arbitrage_andy: ILocalHyperdriveAgent,
    manual_agent: ILocalHyperdriveAgent,
):
    """Open a long to hit the target rate."""
    # change the fixed rate
    manual_agent.open_short(bonds=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_fixed_rate())

    # arbitrage it back (the only trade capable of this is a long)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_short(
    interactive_hyperdrive: ILocalHyperdrive,
    trade_amount: float,
    arbitrage_andy: ILocalHyperdriveAgent,
    manual_agent: ILocalHyperdriveAgent,
):
    """Open a short to hit the target rate."""
    # change the fixed rate
    manual_agent.open_long(base=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_fixed_rate())

    # arbitrage it back (the only trade capable of this is a short)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


# pylint: disable=too-many-locals
@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", [0.003, 10])
def test_close_long(
    interactive_hyperdrive: ILocalHyperdrive,
    trade_amount: float,
    arbitrage_andy: ILocalHyperdriveAgent,
    manual_agent: ILocalHyperdriveAgent,
):
    """Close a long to hit the target rate."""
    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_fixed_rate())

    # give andy a long position twice the trade amount, to be sufficiently large when closing
    pool_bonds_before = interactive_hyperdrive.interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.interface.current_pool_state.block_time
    event = arbitrage_andy.open_long(base=FixedPoint(3 * trade_amount))
    pool_bonds_after = interactive_hyperdrive.interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.interface.current_pool_state.block_time
    d_bonds = pool_bonds_after - pool_bonds_before  # instead of event.bond_amount
    d_shares = pool_shares_after - pool_shares_before  # instead of event.base_amount
    d_time = block_time_after - block_time_before
    logging.info("Andy opened long %s base.", 3 * trade_amount)
    logging.info("Δtime=%s", d_time)
    logging.info(
        " pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares
    )
    logging.info(
        " event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )
    # undo this trade manually
    manual_agent.open_short(bonds=FixedPoint(event.bond_amount * FixedPoint(1.006075)))
    logging.info(
        "manually opened short. event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )

    # report fixed rate
    logging.info("fixed rate is %s", interactive_hyperdrive.interface.calc_fixed_rate())

    # change the fixed rate
    event = manual_agent.open_long(base=FixedPoint(trade_amount))
    logging.info(
        "manually opened short. event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )
    # report fixed rate
    logging.info("fixed rate is %s", interactive_hyperdrive.interface.calc_fixed_rate())

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
    d_shares = pool_shares_after - pool_shares_before  # instead of event.base_amount
    d_time = block_time_after - block_time_before
    logging.info("Andy closed long. amount determined by policy.")
    logging.info("Δtime=%s", d_time)
    logging.info(
        " pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares
    )
    logging.info(
        " event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
def test_already_at_target(interactive_hyperdrive: ILocalHyperdrive, arbitrage_andy: ILocalHyperdriveAgent):
    """Already at target, do nothing."""
    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_fixed_rate())

    # modify Andy to be done_on_empty
    andy_interactive_policy = arbitrage_andy.agent.policy
    assert hasattr(andy_interactive_policy, "sub_policy") and isinstance(
        getattr(andy_interactive_policy, "sub_policy"), PolicyZoo.lp_and_arb
    )
    andy_policy = getattr(andy_interactive_policy, "sub_policy")
    assert hasattr(andy_policy, "policy_config") and isinstance(
        getattr(andy_policy, "policy_config"), PolicyZoo.lp_and_arb.Config
    )
    andy_policy.policy_config.done_on_empty = True

    # arbitrage it back
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
def test_reduce_long(interactive_hyperdrive: ILocalHyperdrive, arbitrage_andy: ILocalHyperdriveAgent):
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
def test_reduce_short(interactive_hyperdrive: ILocalHyperdrive, arbitrage_andy: ILocalHyperdriveAgent):
    """Reduce a short position."""

    logging.info("starting fixed rate is %s", interactive_hyperdrive.interface.calc_fixed_rate())

    # give Andy a short
    event = arbitrage_andy.open_short(bonds=FixedPoint(10))

    logging.info("fixed rate after open short is %s", interactive_hyperdrive.interface.calc_fixed_rate())

    # advance time to maturity
    interactive_hyperdrive.chain.advance_time(int(YEAR_IN_SECONDS / 2), create_checkpoints=False)

    # see if he reduces the short
    event = arbitrage_andy.execute_policy_action()
    event = event[0] if isinstance(event, list) else event
    logging.info("event is %s", event)
    assert isinstance(event, CloseShort)


@pytest.mark.anvil
def test_safe_long_trading(interactive_hyperdrive: ILocalHyperdrive, manual_agent: ILocalHyperdriveAgent):
    """Test that the agent doesn't overextend itself."""
    # setup
    larry_base = FixedPoint(1e4)
    larry_config = PolicyZoo.lp_and_arb.Config(
        lp_portion=FixedPoint("0.99"),
        min_trade_amount_bonds=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    larry = interactive_hyperdrive.init_agent(
        base=larry_base, name="larry", policy=PolicyZoo.lp_and_arb, policy_config=larry_config
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
def test_safe_short_trading(interactive_hyperdrive: ILocalHyperdrive, manual_agent: ILocalHyperdriveAgent):
    """Test that the agent doesn't overextend itself."""
    # setup
    larry_base = FixedPoint(1e4)
    larry_config = PolicyZoo.lp_and_arb.Config(
        lp_portion=FixedPoint("0.9"),
        min_trade_amount_bonds=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    larry = interactive_hyperdrive.init_agent(
        base=larry_base, name="larry", policy=PolicyZoo.lp_and_arb, policy_config=larry_config
    )
    # change the fixed rate
    manual_agent.open_long(base=FixedPoint(100_000))
    # lp & arb
    action_result = larry.execute_policy_action()  # should not be able to arb the full amount after LPing
    # checks
    assert len(action_result) == 2  # LP & Arb (no closing trades)
    assert isinstance(action_result[0], AddLiquidity)  # LP first
    assert isinstance(action_result[1], OpenShort)  # then arb
