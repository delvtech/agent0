"""Test the ability of bots to hit a target rate."""
from __future__ import annotations

import logging

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import LocalChain, InteractiveHyperdrive
from agent0.hyperdrive.policies.zoo import Zoo
from agent0.hyperdrive.interactive.event_types import CloseLong, CloseShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent

# avoid unnecessary warning from using fixtures defined in outer scope
# pylint: disable=redefined-outer-name

TRADE_AMOUNTS = [0.003, 1e4, 1e5]  # 0.003 is three times the minimum transaction amount of local test deploy
# We hit the target rate to the 5th decimal of precision.
# That means 0.050001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-5)
YEAR_IN_SECONDS = 31_536_000


@pytest.fixture(scope="function")
def interactive_hyperdrive(chain: LocalChain) -> InteractiveHyperdrive:
    """Create interactive hyperdrive.

    Arguments
    ---------
    chain: LocalChain
        Local chain.

    Returns
    -------
    InteractiveHyperdrive
        Interactive hyperdrive."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=31_536_000,  # 1 year term
    )
    return InteractiveHyperdrive(chain, interactive_config)


@pytest.fixture(scope="function")
def arbitrage_andy(interactive_hyperdrive) -> InteractiveHyperdriveAgent:
    """Create Arbitrage Andy interactive hyperdrive agent used to arbitrage the fixed rate to the variable rate.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.

    Returns
    -------
    InteractiveHyperdriveAgent
        Arbitrage Andy interactive hyperdrive agent."""
    # create arbitrage andy
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    return interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )


@pytest.fixture(scope="function")
def manual_agent(interactive_hyperdrive) -> InteractiveHyperdriveAgent:
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
    interactive_hyperdrive: InteractiveHyperdrive,
    trade_amount: float,
    arbitrage_andy: InteractiveHyperdriveAgent,
    manual_agent: InteractiveHyperdriveAgent,
):
    """Open a long to hit the target rate."""
    # change the fixed rate
    manual_agent.open_short(bonds=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back (the only trade capable of this is a long)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_short(
    interactive_hyperdrive: InteractiveHyperdrive,
    trade_amount: float,
    arbitrage_andy: InteractiveHyperdriveAgent,
    manual_agent: InteractiveHyperdriveAgent,
):
    """Open a short to hit the target rate."""
    # change the fixed rate
    manual_agent.open_long(base=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back (the only trade capable of this is a short)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", [0.003, 10])
def test_close_long(
    interactive_hyperdrive: InteractiveHyperdrive,
    trade_amount: float,
    arbitrage_andy: InteractiveHyperdriveAgent,
    manual_agent: InteractiveHyperdriveAgent,
):
    """Close a long to hit the target rate."""
    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # give andy a long position twice the trade amount, to be sufficiently large when closing
    pool_bonds_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    event = arbitrage_andy.open_long(base=FixedPoint(3 * trade_amount))
    pool_bonds_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    d_bonds = pool_bonds_after - pool_bonds_before  # instead of event.bond_amount
    d_shares = pool_shares_after - pool_shares_before  # instead of event.base_amount
    d_time = block_time_after - block_time_before
    logging.warning("Andy opened long %s base.", 3 * trade_amount)
    logging.warning("Δtime=%s", d_time)
    logging.warning(
        " pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares
    )
    logging.warning(
        " event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )
    # undo this trade manually
    manual_agent.open_short(bonds=FixedPoint(event.bond_amount * FixedPoint(1.006075)))
    logging.warning(
        "manually opened short. event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )

    # report fixed rate
    logging.warning("fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # change the fixed rate
    event = manual_agent.open_long(base=FixedPoint(trade_amount))
    logging.warning(
        "manually opened short. event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )
    # report fixed rate
    logging.warning("fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it all back in one trade
    pool_bonds_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    event_list = arbitrage_andy.execute_policy_action()
    logging.warning("Andy executed %s", event_list)
    event = event_list[0] if isinstance(event_list, list) else event_list
    assert isinstance(event, CloseLong)
    pool_bonds_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    d_bonds = pool_bonds_after - pool_bonds_before  # instead of event.bond_amount
    d_shares = pool_shares_after - pool_shares_before  # instead of event.base_amount
    d_time = block_time_after - block_time_before
    logging.warning("Andy closed long. amount determined by policy.")
    logging.warning("Δtime=%s", d_time)
    logging.warning(
        " pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares
    )
    logging.warning(
        " event Δbonds= %s%s, Δbase= %s%s",
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
def test_already_at_target(interactive_hyperdrive: InteractiveHyperdrive, arbitrage_andy: InteractiveHyperdriveAgent):
    """Already at target, do nothing."""
    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION
