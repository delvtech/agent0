"""Test the ability of bots to hit a target rate."""

from __future__ import annotations

import logging
from copy import deepcopy

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import LocalChain, InteractiveHyperdrive
from agent0.hyperdrive.policies.zoo import Zoo
from agent0.hyperdrive.interactive.chain import Chain
from agent0.hyperdrive.interactive.event_types import CloseLong, CloseShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent

# avoid unnecessary warning from using fixtures defined in outer scope
# pylint: disable=redefined-outer-name

TRADE_AMOUNTS = [0.003, 1e4, 1e5]  # 0.003 is three times the minimum transaction amount of local test deploy
# We hit the target rate to the 5th decimal of precision.
# That means 0.050001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-5)
YEAR_IN_SECONDS = 31_536_000

# pylint: disable=missing-function-docstring,too-many-statements,logging-fstring-interpolation,missing-return-type-doc
# pylint: disable=missing-return-doc,too-many-function-args


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
        position_duration=YEAR_IN_SECONDS,  # 1 year term
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
    return create_arbitrage_andy(interactive_hyperdrive)


def create_arbitrage_andy(interactive_hyperdrive) -> InteractiveHyperdriveAgent:
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
    logging.info("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back (the only trade capable of this is a long)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
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
    logging.info("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back (the only trade capable of this is a short)
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


# pylint: disable=too-many-locals
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
    logging.info("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

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
    logging.info("fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

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
    logging.info("fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it all back in one trade
    pool_bonds_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    event_list = arbitrage_andy.execute_policy_action()
    logging.info("Andy executed %s", event_list)
    event = event_list[0] if isinstance(event_list, list) else event_list
    assert isinstance(event, CloseLong)
    pool_bonds_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
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
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
def test_already_at_target(interactive_hyperdrive: InteractiveHyperdrive, arbitrage_andy: InteractiveHyperdriveAgent):
    """Already at target, do nothing."""
    # report starting fixed rate
    logging.info("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # modify Andy to be done_on_empty
    andy_interactive_policy = arbitrage_andy.agent.policy
    assert hasattr(andy_interactive_policy, "sub_policy") and isinstance(
        getattr(andy_interactive_policy, "sub_policy"), Zoo.lp_and_arb
    )
    andy_policy = getattr(andy_interactive_policy, "sub_policy")
    assert hasattr(andy_policy, "policy_config") and isinstance(
        getattr(andy_policy, "policy_config"), Zoo.lp_and_arb.Config
    )
    andy_policy.policy_config.done_on_empty = True

    # arbitrage it back
    arbitrage_andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.info("ending fixed rate is %s", fixed_rate)
    logging.info("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.info("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
def test_reduce_long(interactive_hyperdrive: InteractiveHyperdrive, arbitrage_andy: InteractiveHyperdriveAgent):
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
def test_reduce_short(interactive_hyperdrive: InteractiveHyperdrive, arbitrage_andy: InteractiveHyperdriveAgent):
    """Reduce a short position."""

    logging.info("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # give Andy a short
    event = arbitrage_andy.open_short(bonds=FixedPoint(10))

    logging.info("fixed rate after open short is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # advance time to maturity
    interactive_hyperdrive.chain.advance_time(int(YEAR_IN_SECONDS / 2), create_checkpoints=False)

    # see if he reduces the short
    event = arbitrage_andy.execute_policy_action()
    event = event[0] if isinstance(event, list) else event
    logging.info("event is %s", event)
    assert isinstance(event, CloseShort)


@pytest.mark.anvil
def test_predict_open_long(chain: Chain):
    """Predict oucome of an open long."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    arbitrage_andy = create_arbitrage_andy(interactive_hyperdrive=interactive_hyperdrive)
    pool_state = deepcopy(interactive_hyperdrive.hyperdrive_interface.current_pool_state)
    starting_bond_reserves = pool_state.pool_info.bond_reserves
    starting_share_reserves = pool_state.pool_info.share_reserves
    stating_price = interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state)
    logging.info("starting bond_reserves is %s (%s)", starting_bond_reserves, type(starting_bond_reserves).__name__)
    logging.info("starting share_reserves is %s (%s)", starting_share_reserves, type(starting_share_reserves).__name__)
    logging.info("starting spot price is %s (%s)", stating_price, type(stating_price).__name__)

    # start with bonds_needed, convert to base_needed
    bonds_needed = FixedPoint(100_000)
    spot_price = interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    shares_needed = interactive_hyperdrive.hyperdrive_interface.calc_shares_in_given_bonds_out_down(bonds_needed)
    share_price = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_price
    base_needed = shares_needed * share_price
    # use rust to predict trade outcome
    bonds_after_fees = interactive_hyperdrive.hyperdrive_interface.calc_open_long(base_needed)
    logging.info("bonds_after_fees is %s", bonds_after_fees)
    bond_fees = bonds_after_fees * price_discount * curve_fee
    bond_fees_to_pool = bond_fees * (FixedPoint(1) - governance_fee)
    bond_fees_to_gov = bond_fees * governance_fee
    bonds_before_fees = bonds_after_fees + bond_fees_to_pool + bond_fees_to_gov
    logging.info("bonds_before_fees is %s", bonds_before_fees)
    logging.info("bond_fees_to_pool is %s", bond_fees_to_pool)
    logging.info("bond_fees_to_gov is %s", bond_fees_to_gov)

    predicted_delta_bonds = -bonds_after_fees - bond_fees_to_gov
    predicted_delta_shares = base_needed / share_price * (FixedPoint(1) - price_discount * curve_fee * governance_fee)
    logging.info("predicted delta bonds is %s", predicted_delta_bonds)
    logging.info("predicted delta shares is %s", predicted_delta_shares)

    # measure pool before trade
    pool_state_before = deepcopy(interactive_hyperdrive.hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    # do the trade
    event = arbitrage_andy.open_long(base=base_needed)
    event = event[0] if isinstance(event, list) else event
    actual_event_bonds = event.bond_amount
    actual_event_base = event.base_amount
    logging.info(
        "opened long with input base=%s, output Δbonds= %s%s, Δbase= %s%s",
        base_needed,
        "+" if actual_event_bonds > 0 else "",
        actual_event_bonds,
        "+" if actual_event_base > 0 else "",
        actual_event_base,
    )
    # measure pool after trade
    pool_state_after = deepcopy(interactive_hyperdrive.hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    logging.info("pool bonds after is %s", pool_bonds_after)
    logging.info("pool shares after is %s", pool_shares_after)
    actual_delta_bonds = pool_bonds_after - pool_bonds_before
    actual_delta_shares = pool_shares_after - pool_shares_before
    logging.info("actual delta bonds is %s", actual_delta_bonds)
    logging.info("actual delta shares is %s", actual_delta_shares)

    bonds_discrepancy = float((actual_delta_bonds - predicted_delta_bonds) / predicted_delta_bonds)
    shares_discrepancy = float((actual_delta_shares - predicted_delta_shares) / predicted_delta_shares)
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")  # pylint: disable=logging-fstring-interpolation
    logging.info(
        f"discrepancy (%) for shares is {shares_discrepancy:e}"
    )  # pylint: disable=logging-fstring-interpolation

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7


@pytest.mark.anvil
def test_predict_open_short(chain: Chain):
    """Predict oucome of an open short."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    arbitrage_andy = create_arbitrage_andy(interactive_hyperdrive=interactive_hyperdrive)
    pool_state = deepcopy(interactive_hyperdrive.hyperdrive_interface.current_pool_state)
    starting_bond_reserves = pool_state.pool_info.bond_reserves
    starting_share_reserves = pool_state.pool_info.share_reserves
    stating_price = interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state)
    logging.info("starting bond_reserves is %s (%s)", starting_bond_reserves, type(starting_bond_reserves).__name__)
    logging.info("starting share_reserves is %s (%s)", starting_share_reserves, type(starting_share_reserves).__name__)
    logging.info("starting spot price is %s (%s)", stating_price, type(stating_price).__name__)

    # start with bonds_needed, convert to base_needed
    bonds_needed = FixedPoint(100_000)
    spot_price = interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    # use rust to predict trade outcome
    shares_before_fees = interactive_hyperdrive.hyperdrive_interface.calc_shares_out_given_bonds_in_down(bonds_needed)
    logging.info("shares_before_fees is %s", shares_before_fees)
    fees = bonds_needed * price_discount * curve_fee
    fees_to_pool = fees * (FixedPoint(1) - governance_fee)
    fees_to_gov = fees * governance_fee
    shares_after_fees = shares_before_fees + fees_to_pool + fees_to_gov
    logging.info("shares_after_fees is %s", shares_after_fees)
    logging.info("fees_to_pool is %s", fees_to_pool)
    logging.info("fees_to_gov is %s", fees_to_gov)

    predicted_delta_bonds = bonds_needed
    predicted_delta_shares = -shares_before_fees + fees_to_pool
    logging.info("predicted delta bonds is %s", predicted_delta_bonds)
    logging.info("predicted delta shares is %s", predicted_delta_shares)

    # # measure pool before trade
    pool_state_before = deepcopy(interactive_hyperdrive.hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    # # do the trade
    event = arbitrage_andy.open_short(bonds=bonds_needed)
    event = event[0] if isinstance(event, list) else event
    actual_event_bonds = event.bond_amount
    actual_event_base = event.base_amount
    logging.info(
        "opened short with input base=%s, output Δbonds= %s%s, Δbase= %s%s",
        bonds_needed,
        "+" if actual_event_bonds > 0 else "",
        actual_event_bonds,
        "+" if actual_event_base > 0 else "",
        actual_event_base,
    )
    # # measure pool after trade
    pool_state_after = deepcopy(interactive_hyperdrive.hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    logging.info("pool bonds after is %s", pool_bonds_after)
    logging.info("pool shares after is %s", pool_shares_after)
    actual_delta_bonds = pool_bonds_after - pool_bonds_before
    actual_delta_shares = pool_shares_after - pool_shares_before
    logging.info("actual delta bonds is %s", actual_delta_bonds)
    logging.info("actual delta shares is %s", actual_delta_shares)

    bonds_discrepancy = float((actual_delta_bonds - predicted_delta_bonds) / predicted_delta_bonds)
    shares_discrepancy = float((actual_delta_shares - predicted_delta_shares) / predicted_delta_shares)
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")  # pylint: disable=logging-fstring-interpolation
    logging.info(
        f"discrepancy (%) for shares is {shares_discrepancy:e}"
    )  # pylint: disable=logging-fstring-interpolation

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7
