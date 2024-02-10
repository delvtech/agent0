"""Test the ability of bots to hit a target rate."""

from __future__ import annotations

import logging
from copy import deepcopy
from decimal import Decimal
from typing import NamedTuple

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.chain import Chain
from agent0.hyperdrive.interactive.event_types import CloseLong, CloseShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.policies import PolicyZoo
from ethpy.hyperdrive.interface.read_interface import HyperdriveReadInterface
from ethpy.hyperdrive.state import PoolState

# avoid unnecessary warning from using fixtures defined in outer scope
# pylint: disable=redefined-outer-name

TRADE_AMOUNTS = [0.003, 1e4, 1e5]  # 0.003 is three times the minimum transaction amount of local test deploy
# We hit the target rate to the 5th decimal of precision.
# That means 0.050001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-5)
YEAR_IN_SECONDS = 31_536_000
BLOCKS_IN_YEAR = YEAR_IN_SECONDS/12

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
    andy_config = PolicyZoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    return interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=PolicyZoo.lp_and_arb, policy_config=andy_config
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
    interactive_hyperdrive: InteractiveHyperdrive,
    trade_amount: float,
    arbitrage_andy: InteractiveHyperdriveAgent,
    manual_agent: InteractiveHyperdriveAgent,
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
    interactive_hyperdrive: InteractiveHyperdrive,
    trade_amount: float,
    arbitrage_andy: InteractiveHyperdriveAgent,
    manual_agent: InteractiveHyperdriveAgent,
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
def test_already_at_target(interactive_hyperdrive: InteractiveHyperdrive, arbitrage_andy: InteractiveHyperdriveAgent):
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

Deltas = NamedTuple("Deltas", [("base", FixedPoint), ("bonds", FixedPoint), ("shares", FixedPoint)])
TradeDeltas = NamedTuple("TradeDeltas", [("user", Deltas), ("pool", Deltas), ("fee", Deltas), ("governance", Deltas)])

def predict_long(hyperdrive_interface: HyperdriveReadInterface, pool_state: PoolState|None = None, base:FixedPoint|None=None, bonds:FixedPoint|None=None, verbose: bool = False) -> TradeDeltas:
    if pool_state is None:
        pool_state = deepcopy(hyperdrive_interface.current_pool_state)
    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    if base is not None and bonds is None:
        base_needed = base
    elif bonds is not None and base is None:
        # we need to calculate base_needed
        bonds_needed = bonds
        shares_needed = hyperdrive_interface.calc_shares_in_given_bonds_out_up(bonds_needed)
        shares_needed /= FixedPoint(1) - price_discount * curve_fee
        share_price_on_next_block = share_price * (FixedPoint(1)+hyperdrive_interface.get_variable_rate(pool_state.block_number)/FixedPoint(BLOCKS_IN_YEAR))
        base_needed = shares_needed * share_price_on_next_block
    else:
        raise ValueError("predict_long(): Need to specify either bonds or base, but not both.")
    # continue with common logic, now that we have base_needed
    assert base_needed is not None
    bonds_after_fees = hyperdrive_interface.calc_open_long(base_needed)
    if verbose:
        logging.info("predict_long(): bonds_after_fees is %s", bonds_after_fees)
    bond_fees = bonds_after_fees * price_discount * curve_fee
    bond_fees_to_pool = bond_fees * (FixedPoint(1) - governance_fee)
    bond_fees_to_gov = bond_fees * governance_fee
    bonds_before_fees = bonds_after_fees + bond_fees_to_pool + bond_fees_to_gov
    if verbose:
        logging.info("predict_long(): bonds_before_fees is %s", bonds_before_fees)
        logging.info("predict_long(): bond_fees_to_pool is %s", bond_fees_to_pool)
        logging.info("predict_long(): bond_fees_to_gov is %s", bond_fees_to_gov)
    predicted_delta_bonds = -bonds_after_fees - bond_fees_to_gov
    # gov_scaling factor is the ratio by which we lower the change in base and increase the change in shares
    # this is done to take into account the effect of the governance fee on pool reserves
    gov_scaling_factor = (FixedPoint(1) - price_discount * curve_fee * governance_fee)
    predicted_delta_base = base_needed * gov_scaling_factor
    # predicted_delta_shares = predicted_delta_bonds / share_price
    predicted_delta_shares = base_needed / share_price * gov_scaling_factor
    if verbose:
        logging.info("predict_long(): predicted delta bonds is %s", predicted_delta_bonds)
        logging.info("predict_long(): predicted delta shares is %s", predicted_delta_shares)
    return TradeDeltas(
        user=Deltas(bonds=bonds_after_fees,base=base_needed,shares=base_needed/share_price),
        pool=Deltas(base=predicted_delta_base, shares=predicted_delta_shares, bonds=predicted_delta_bonds),
        fee=Deltas(bonds=bond_fees_to_pool, base=bond_fees_to_pool*spot_price, shares=bond_fees_to_pool*spot_price*share_price),
        governance=Deltas(bonds=bond_fees_to_gov, base=bond_fees_to_gov*spot_price, shares=bond_fees_to_gov*spot_price*share_price),
        )

def predict_short(hyperdrive_interface: HyperdriveReadInterface, pool_state: PoolState|None = None, base:FixedPoint|None=None, bonds:FixedPoint|None=None, verbose: bool = False) -> TradeDeltas:
    if pool_state is None:
        pool_state = deepcopy(hyperdrive_interface.current_pool_state)
    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    if bonds is not None and base is None:
        bonds_needed = bonds
    elif base is not None and bonds is None:
        # we need to calculate bonds_needed
        base_needed = base
        # bonds_needed = hyperdrive_interface.calc_bonds_in_given_shares_out(base_needed / share_price)
        # this is the wrong direction for the swap, but we don't have the function in the other direction
        bonds_needed = hyperdrive_interface.calc_bonds_out_given_shares_in_down(base_needed / share_price)
        bonds_needed /= (FixedPoint(1) - price_discount * curve_fee * (FixedPoint(1) - governance_fee))
    else:
        raise ValueError("predict_short(): Need to specify either bonds or base, but not both.")
    shares_before_fees = hyperdrive_interface.calc_shares_out_given_bonds_in_down(bonds_needed)
    base_fees = bonds_needed * price_discount * curve_fee
    base_fees_to_pool = base_fees * (FixedPoint(1) - governance_fee)
    base_fees_to_gov = base_fees * governance_fee
    shares_after_fees = shares_before_fees + base_fees_to_pool + base_fees_to_gov
    base_after_fees = shares_after_fees * share_price
    if verbose:
        logging.info("predict_short(): shares_before_fees is %s", shares_before_fees)
        logging.info("predict_short(): shares_after_fees is %s", shares_after_fees)
        logging.info("predict_short(): base_fees_to_pool is %s", base_fees_to_pool)
        logging.info("predict_short(): base_fees_to_gov is %s", base_fees_to_gov)
    predicted_delta_bonds = bonds_needed
    predicted_delta_shares = -shares_before_fees + base_fees_to_pool
    predicted_delta_base = predicted_delta_shares * share_price
    if verbose:
        logging.info("predict_short(): predicted delta bonds is %s", predicted_delta_bonds)
        logging.info("predict_short(): predicted delta shares is %s", predicted_delta_shares)
    return TradeDeltas(
        user=Deltas(bonds=bonds_needed,base=base_after_fees,shares=shares_after_fees),
        pool=Deltas(base=predicted_delta_base, shares=predicted_delta_shares, bonds=predicted_delta_bonds),
        fee=Deltas(bonds=base_fees_to_pool/spot_price, base=base_fees_to_pool, shares=base_fees_to_pool/share_price),
        governance=Deltas(bonds=base_fees_to_gov/spot_price, base=base_fees_to_gov, shares=base_fees_to_gov/share_price),
        )
    

@pytest.mark.anvil
def test_predict_open_long_bonds(chain: Chain):
    """Predict outcome of an open long, for a given amount of bonds."""
    # setup
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    arbitrage_andy = create_arbitrage_andy(interactive_hyperdrive=interactive_hyperdrive)
    pool_state = deepcopy(hyperdrive_interface.current_pool_state)
    starting_bond_reserves = pool_state.pool_info.bond_reserves
    starting_share_reserves = pool_state.pool_info.share_reserves
    stating_price = hyperdrive_interface.calc_spot_price(pool_state)
    logging.info("starting bond_reserves is %s (%s)", starting_bond_reserves, type(starting_bond_reserves).__name__)
    logging.info("starting share_reserves is %s (%s)", starting_share_reserves, type(starting_share_reserves).__name__)
    logging.info("starting spot price is %s (%s)", stating_price, type(stating_price).__name__)

    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    # convert from bonds to base, if needed
    bonds_needed = FixedPoint(100_000)
    shares_needed = hyperdrive_interface.calc_shares_in_given_bonds_out_up(bonds_needed)
    shares_needed /= (FixedPoint(1) - price_discount * curve_fee)
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    share_price_on_next_block = share_price * (FixedPoint(1)+hyperdrive_interface.get_variable_rate(pool_state.block_number)/FixedPoint(BLOCKS_IN_YEAR))
    base_needed = shares_needed * share_price_on_next_block
    # use rust to predict trade outcome
    bonds_after_fees = hyperdrive_interface.calc_open_long(base_needed)
    delta = predict_long(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed, verbose=True)
    assert bonds_after_fees == delta.user.bonds
    bond_fees = bonds_after_fees * price_discount * curve_fee
    bond_fees_to_pool = bond_fees * (FixedPoint(1) - governance_fee)
    assert bond_fees_to_pool == delta.fee.bonds
    bond_fees_to_gov = bond_fees * governance_fee
    assert bond_fees_to_gov == delta.governance.bonds
    bonds_before_fees = bonds_after_fees + bond_fees_to_pool + bond_fees_to_gov
    logging.info("bond_fees_to_pool is %s", bond_fees_to_pool)
    logging.info("bond_fees_to_gov is %s", bond_fees_to_gov)

    predicted_delta_bonds = -bonds_after_fees - bond_fees_to_gov
    assert predicted_delta_bonds == delta.pool.bonds
    predicted_delta_shares = base_needed / share_price * (FixedPoint(1) - price_discount * curve_fee * governance_fee)
    assert predicted_delta_shares == delta.pool.shares
    logging.info("predicted pool delta bonds is %s", predicted_delta_bonds)
    logging.info("predicted pool delta shares is %s", predicted_delta_shares)

    # measure user wallet before trade
    user_base_before = arbitrage_andy.agent.wallet.balance.amount
    # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * pool_state_before.pool_info.vault_share_price
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
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
    logging.info("pool bonds after is %s", pool_bonds_after)
    logging.info("pool shares after is %s", pool_shares_after)
    actual_delta_bonds = pool_bonds_after - pool_bonds_before
    actual_delta_shares = pool_shares_after - pool_shares_before
    actual_delta_base = pool_base_after - pool_base_before
    logging.info("actual pool delta bonds is %s", actual_delta_bonds)
    logging.info("actual pool delta shares is %s", actual_delta_shares)
    logging.info("actual pool delta base is %s", actual_delta_base)
    # measure user's outcome after the trade
    # does our prediction match the input
    assert abs(Decimal(str(delta.user.base - base_needed))) < 1e-16
    # does the actual outcome match the prediction
    user_base_after = arbitrage_andy.agent.wallet.balance.amount
    actual_delta_user_base = user_base_before - user_base_after
    logging.info("actual user delta base is %s", actual_delta_user_base)
    assert abs(Decimal(str(actual_delta_user_base - base_needed))) < 1e-16
    actual_delta_user_bonds = list(arbitrage_andy.agent.wallet.longs.values())[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert abs(Decimal(str(actual_delta_user_bonds - bonds_needed))) < 1e-3

    bonds_discrepancy = Decimal(str((actual_delta_bonds - predicted_delta_bonds) / predicted_delta_bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - predicted_delta_shares) / predicted_delta_shares))
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy:e}")

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7

@pytest.mark.anvil
def test_predict_open_long_base(chain: Chain):
    """Predict outcome of an open long, for a given amount of base."""
    # setup
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    arbitrage_andy = create_arbitrage_andy(interactive_hyperdrive=interactive_hyperdrive)
    pool_state = deepcopy(hyperdrive_interface.current_pool_state)
    starting_bond_reserves = pool_state.pool_info.bond_reserves
    starting_share_reserves = pool_state.pool_info.share_reserves
    stating_price = hyperdrive_interface.calc_spot_price(pool_state)
    logging.info("starting bond_reserves is %s (%s)", starting_bond_reserves, type(starting_bond_reserves).__name__)
    logging.info("starting share_reserves is %s (%s)", starting_share_reserves, type(starting_share_reserves).__name__)
    logging.info("starting spot price is %s (%s)", stating_price, type(stating_price).__name__)

    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    base_needed = FixedPoint(100_000)
    # use rust to predict trade outcome
    bonds_after_fees = hyperdrive_interface.calc_open_long(base_needed)
    delta = predict_long(hyperdrive_interface=hyperdrive_interface, base=base_needed, verbose=True)
    assert bonds_after_fees == delta.user.bonds
    bond_fees = bonds_after_fees * price_discount * curve_fee
    bond_fees_to_pool = bond_fees * (FixedPoint(1) - governance_fee)
    assert bond_fees_to_pool == delta.fee.bonds
    bond_fees_to_gov = bond_fees * governance_fee
    assert bond_fees_to_gov == delta.governance.bonds
    bonds_before_fees = bonds_after_fees + bond_fees_to_pool + bond_fees_to_gov
    logging.info("bond_fees_to_pool is %s", bond_fees_to_pool)
    logging.info("bond_fees_to_gov is %s", bond_fees_to_gov)

    predicted_delta_bonds = -bonds_after_fees - bond_fees_to_gov
    assert predicted_delta_bonds == delta.pool.bonds
    predicted_delta_shares = base_needed / share_price * (FixedPoint(1) - price_discount * curve_fee * governance_fee)
    assert predicted_delta_shares == delta.pool.shares
    predicted_delta_base = predicted_delta_shares * share_price
    assert abs(Decimal(str(predicted_delta_base - delta.pool.base))) < 1e-16
    logging.info("predicted delta bonds is %s", predicted_delta_bonds)
    logging.info("predicted delta shares is %s", predicted_delta_shares)
    logging.info("predicted delta base is %s", predicted_delta_base)

    # measure user wallet before trade
    user_base_before = arbitrage_andy.agent.wallet.balance.amount
    # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * pool_state_before.pool_info.vault_share_price
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
    # measure pool's outcome after trade
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
    logging.info("pool bonds after is %s", pool_bonds_after)
    logging.info("pool shares after is %s", pool_shares_after)
    logging.info("pool base after is %s", pool_base_after)
    actual_delta_bonds = pool_bonds_after - pool_bonds_before
    actual_delta_shares = pool_shares_after - pool_shares_before
    actual_delta_base = pool_base_after - pool_base_before
    logging.info("actual pool delta bonds is %s", actual_delta_bonds)
    logging.info("actual pool delta shares is %s", actual_delta_shares)
    logging.info("actual pool delta base is %s", actual_delta_base)
    # measure user's outcome after the trade
    # does our prediction match the input
    assert abs(Decimal(str(delta.user.base - base_needed))) < 1e-16
    # does the actual outcome match the prediction
    user_base_after = arbitrage_andy.agent.wallet.balance.amount
    actual_delta_user_base = user_base_before - user_base_after
    logging.info("actual user delta base is %s", actual_delta_user_base)
    assert abs(Decimal(str(actual_delta_user_base - base_needed))) < 1e-16

    bonds_discrepancy = Decimal(str((actual_delta_bonds - predicted_delta_bonds) / predicted_delta_bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - predicted_delta_shares) / predicted_delta_shares))
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy:e}")

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7

@pytest.mark.anvil
def test_predict_open_short_bonds(chain: Chain):
    """Predict oucome of an open short, for a given amount of bonds."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    arbitrage_andy = create_arbitrage_andy(interactive_hyperdrive=interactive_hyperdrive)
    pool_state = deepcopy(interactive_hyperdrive.interface.current_pool_state)
    starting_bond_reserves = pool_state.pool_info.bond_reserves
    starting_share_reserves = pool_state.pool_info.share_reserves
    stating_price = hyperdrive_interface.calc_spot_price(pool_state)
    logging.info("starting bond_reserves is %s (%s)", starting_bond_reserves, type(starting_bond_reserves).__name__)
    logging.info("starting share_reserves is %s (%s)", starting_share_reserves, type(starting_share_reserves).__name__)
    logging.info("starting spot price is %s (%s)", stating_price, type(stating_price).__name__)

    bonds_needed = FixedPoint(100_000)
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    # use rust to predict trade outcome
    shares_before_fees = hyperdrive_interface.calc_shares_out_given_bonds_in_down(bonds_needed)
    delta = predict_short(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed, verbose=True)
    logging.info("shares_before_fees is %s", shares_before_fees)
    base_fees = bonds_needed * price_discount * curve_fee
    base_fees_to_pool = base_fees * (FixedPoint(1) - governance_fee)
    assert base_fees_to_pool == delta.fee.base
    base_fees_to_gov = base_fees * governance_fee
    assert base_fees_to_gov == delta.governance.base
    shares_after_fees = shares_before_fees + base_fees_to_pool + base_fees_to_gov
    assert shares_after_fees == delta.user.shares
    logging.info("shares_after_fees is %s", shares_after_fees)
    logging.info("base_fees_to_pool is %s", base_fees_to_pool)
    logging.info("base_fees_to_gov is %s", base_fees_to_gov)

    predicted_delta_bonds = bonds_needed
    assert predicted_delta_bonds == delta.pool.bonds
    predicted_delta_shares = -shares_before_fees + base_fees_to_pool
    assert predicted_delta_shares == delta.pool.shares
    predicted_delta_base = predicted_delta_shares * share_price
    logging.info("predicted pool delta bonds is %s", predicted_delta_bonds)
    logging.info("predicted pool delta shares is %s", predicted_delta_shares)
    logging.info("predicted pool delta base is %s", predicted_delta_base)

    # measure user wallet before trade
    user_base_before = arbitrage_andy.agent.wallet.balance.amount
    # # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * stating_price
    # # do the trade
    event = arbitrage_andy.open_short(bonds=bonds_needed)
    event = event[0] if isinstance(event, list) else event
    actual_event_bonds = event.bond_amount
    actual_event_base = event.base_amount
    logging.info(
        "opened short with input bonds=%s, output Δbonds= %s%s, Δbase= %s%s",
        bonds_needed,
        "+" if actual_event_bonds > 0 else "",
        actual_event_bonds,
        "+" if actual_event_base > 0 else "",
        actual_event_base,
    )
    # # measure pool after trade
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
    logging.info("pool bonds after is %s", pool_bonds_after)
    logging.info("pool shares after is %s", pool_shares_after)
    logging.info("pool base after is %s", pool_base_after)
    actual_delta_bonds = pool_bonds_after - pool_bonds_before
    actual_delta_shares = pool_shares_after - pool_shares_before
    actual_delta_base = pool_base_after - pool_base_before
    logging.info("actual delta bonds is %s", actual_delta_bonds)
    logging.info("actual delta shares is %s", actual_delta_shares)
    logging.info("actual pool delta base is %s", actual_delta_base)
    # measure user's outcome after the trade
    # does our prediction match the input
    assert abs(Decimal(str(delta.user.bonds - bonds_needed))) < 1e-16
    # does the actual outcome match the prediction
    user_base_after = arbitrage_andy.agent.wallet.balance.amount
    actual_delta_user_base = user_base_before - user_base_after
    logging.info("actual user delta base is %s", actual_delta_user_base)
    actual_delta_user_bonds = list(arbitrage_andy.agent.wallet.shorts.values())[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert abs(Decimal(str(actual_delta_user_bonds - bonds_needed))) < 1e-3

    bonds_discrepancy = Decimal(str((actual_delta_bonds - predicted_delta_bonds) / predicted_delta_bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - predicted_delta_shares) / predicted_delta_shares))
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")  # pylint: disable=logging-fstring-interpolation
    logging.info(
        f"discrepancy (%) for shares is {shares_discrepancy:e}"
    )  # pylint: disable=logging-fstring-interpolation

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7

@pytest.mark.anvil
def test_predict_open_short_base(chain: Chain):
    """Predict oucome of an open short, for a given amount of base."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    arbitrage_andy = create_arbitrage_andy(interactive_hyperdrive=interactive_hyperdrive)
    pool_state = deepcopy(interactive_hyperdrive.interface.current_pool_state)
    starting_bond_reserves = pool_state.pool_info.bond_reserves
    starting_share_reserves = pool_state.pool_info.share_reserves
    stating_price = hyperdrive_interface.calc_spot_price(pool_state)
    logging.info("starting bond_reserves is %s (%s)", starting_bond_reserves, type(starting_bond_reserves).__name__)
    logging.info("starting share_reserves is %s (%s)", starting_share_reserves, type(starting_share_reserves).__name__)
    logging.info("starting spot price is %s (%s)", stating_price, type(stating_price).__name__)

    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    # start with base_needed, convert to bonds_needed
    base_needed = FixedPoint(100_000)
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    # this is the wrong direction for the swap, but we don't have the function in the other direction
    bonds_needed = hyperdrive_interface.calc_bonds_out_given_shares_in_down((base_needed / hyperdrive_interface.current_pool_state.pool_info.vault_share_price))
    # adjust for fees
    # bonds_needed /= (FixedPoint(1) - price_discount * curve_fee)
    logging.info("bonds_needed is %s", bonds_needed)
    # use rust to predict trade outcome
    shares_before_fees = hyperdrive_interface.calc_shares_out_given_bonds_in_down(bonds_needed)
    delta = predict_short(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed, verbose=True)
    logging.info("shares_before_fees is %s", shares_before_fees)
    base_fees = bonds_needed * price_discount * curve_fee
    base_fees_to_pool = base_fees * (FixedPoint(1) - governance_fee)
    assert base_fees_to_pool == delta.fee.base
    base_fees_to_gov = base_fees * governance_fee
    assert base_fees_to_gov == delta.governance.base
    shares_after_fees = shares_before_fees + base_fees_to_pool + base_fees_to_gov
    assert shares_after_fees == delta.user.shares
    logging.info("shares_after_fees is %s", shares_after_fees)
    logging.info("base_fees_to_pool is %s", base_fees_to_pool)
    logging.info("base_fees_to_gov is %s", base_fees_to_gov)

    predicted_delta_bonds = bonds_needed
    assert predicted_delta_bonds == delta.pool.bonds
    predicted_delta_shares = -shares_before_fees + base_fees_to_pool
    assert predicted_delta_shares == delta.pool.shares
    predicted_delta_base = predicted_delta_shares * share_price
    logging.info("predicted delta bonds is %s", predicted_delta_bonds)
    logging.info("predicted delta shares is %s", predicted_delta_shares)
    logging.info("predicted delta base is %s", predicted_delta_base)

    # measure user wallet before trade
    user_base_before = arbitrage_andy.agent.wallet.balance.amount
    # # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * share_price
    # # do the trade
    event = arbitrage_andy.open_short(bonds=bonds_needed)
    event = event[0] if isinstance(event, list) else event
    actual_event_bonds = event.bond_amount
    actual_event_base = event.base_amount
    logging.info(
        "opened short with input bonds=%s, output Δbonds= %s%s, Δbase= %s%s",
        bonds_needed,
        "+" if actual_event_bonds > 0 else "",
        actual_event_bonds,
        "+" if actual_event_base > 0 else "",
        actual_event_base,
    )
    # # measure pool after trade
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
    logging.info("pool bonds after is %s", pool_bonds_after)
    logging.info("pool shares after is %s", pool_shares_after)
    logging.info("pool base after is %s", pool_base_after)
    actual_delta_bonds = pool_bonds_after - pool_bonds_before
    actual_delta_shares = pool_shares_after - pool_shares_before
    actual_delta_base = pool_base_after - pool_base_before
    logging.info("actual pool delta bonds is %s", actual_delta_bonds)
    logging.info("actual pool delta shares is %s", actual_delta_shares)
    logging.info("actual pool delta base is %s", actual_delta_base)
    # measure user's outcome after the trade
    # does our prediction match the input
    assert abs(Decimal(str(delta.user.bonds - bonds_needed))) < 1e-16
    # does the actual outcome match the prediction
    user_base_after = arbitrage_andy.agent.wallet.balance.amount
    actual_delta_user_base = user_base_before - user_base_after
    logging.info("actual user delta base is %s", actual_delta_user_base)
    actual_delta_user_bonds = list(arbitrage_andy.agent.wallet.shorts.values())[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert abs(Decimal(str(actual_delta_user_bonds - bonds_needed))) < 1e-3

    bonds_discrepancy = Decimal(str((actual_delta_bonds - predicted_delta_bonds) / predicted_delta_bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - predicted_delta_shares) / predicted_delta_shares))
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")  # pylint: disable=logging-fstring-interpolation
    logging.info(
        f"discrepancy (%) for shares is {shares_discrepancy:e}"
    )  # pylint: disable=logging-fstring-interpolation

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7

@pytest.mark.anvil
def test_asymmetry(chain: Chain):
    """Does in equal out?"""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    interface = interactive_hyperdrive.interface
    x = interface.calc_shares_out_given_bonds_in_down(FixedPoint(100_000))
    y = interface.calc_shares_in_given_bonds_out_down(FixedPoint(100_000))
    print(x)
    print(y)
    assert x != y
