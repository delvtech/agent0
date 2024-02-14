"""Test our ability to predict the outcome of a trade, with an input of bonds or base being traded.

A trade results in changes to 4 accounts, measured in 3 units.
    accounts: pool, user, fee, governance
    units: base, bonds, shares
Knowing the impact on each of these ahead of time can be useful, depending on the application.
    This is useful for deciding how much to trade.
    LP and Arb bot uses this logic to hit a target rate.
3 tests are simple demonstrations of how to do a prediction.
    Simplest case: test_prediction_example
    Open long with bonds as input: test_open_long_bonds
    Open short with base as input: test_open_short_base
4 tests check prediction accuracy, spanning the cases of opening a long/short with bonds/base as inputs.
    Open long:
        with bonds as input: test_predict_open_long_bonds
        with base as input: test_predict_open_long_base
    Open short:
        with bonds as input: test_predict_open_short_bonds
        with base as input: test_predict_open_short_base
The four prediction tests check:
- does our prediction match the input?
- predicted delta matches actual delta (for user and pool)
"""

from __future__ import annotations

import logging
from copy import deepcopy
from decimal import Decimal
from typing import NamedTuple

import pytest
from ethpy.hyperdrive.interface.read_interface import HyperdriveReadInterface
from ethpy.hyperdrive.state import PoolState
from fixedpointmath import FixedPoint
from tabulate import tabulate

from agent0.hyperdrive.interactive import InteractiveHyperdrive
from agent0.hyperdrive.interactive.chain import Chain
from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort

# it's just a test
# pylint: disable=logging-fstring-interpolation
# pylint: disable=too-many-locals
# allow magic value comparison (like < 1e-16)
# ruff: noqa: PLR2004
# allow lots of statements
# ruff: noqa: PLR0915

YEAR_IN_SECONDS = 31_536_000
BLOCKS_IN_YEAR = YEAR_IN_SECONDS / 12

Deltas = NamedTuple(
    "Deltas",
    [
        ("base", FixedPoint),
        ("bonds", FixedPoint),
        ("shares", FixedPoint),
    ],
)
TradeDeltas = NamedTuple(
    "TradeDeltas",
    [
        ("user", Deltas),
        ("pool", Deltas),
        ("fee", Deltas),
        ("governance", Deltas),
    ],
)


def _format_table(delta: TradeDeltas):
    formatted_data = [
        [account] + [float(metric) for metric in getattr(delta, account)]
        for account in ["user", "pool", "fee", "governance"]
    ]
    return tabulate(formatted_data, headers=["Entity", "Base", "Bonds", "Shares"], tablefmt="grid")


def _print_table(delta: TradeDeltas):
    print("\n", end="")
    print(_format_table(delta))


def _log_table(delta: TradeDeltas):
    logging.info("\n%s", _format_table(delta))


def _log_event(
    trade_type: str,
    input_type: str,
    base_needed: FixedPoint,
    event: OpenLong | OpenShort,
):
    logging.info(
        "opened %s with input %s=%s, output Δbonds= %s%s, Δbase= %s%s",
        trade_type,
        input_type,
        base_needed,
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.base_amount > 0 else "",
        event.base_amount,
    )


def test_prediction_example(chain: Chain):
    """Demonstrate the simplest case of a prediction.

    Output:
        +------------+--------------+---------------+--------------+
        | Entity     |         Base |         Bonds |       Shares |
        +============+==============+===============+==============+
        | user       | 100          |  104.95       | 100          |
        +------------+--------------+---------------+--------------+
        | pool       |  99.9952     | -104.955      |  99.9952     |
        +------------+--------------+---------------+--------------+
        | fee        |   0.0428367  |    0.0449786  |   0.0428367  |
        +------------+--------------+---------------+--------------+
        | governance |   0.00475964 |    0.00499762 |   0.00475964 |
        +------------+--------------+---------------+--------------+
    """
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))
    base_needed = FixedPoint(100)
    delta = predict_long(hyperdrive_interface=interactive_hyperdrive.interface, base=base_needed)
    event = agent.open_long(base=base_needed)
    _log_event("long", "base", base_needed, event[0] if isinstance(event, list) else event)
    _log_table(delta)


def test_open_long_bonds(chain: Chain):
    """Demonstrate abililty to open long with bonds as input."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))

    bonds_needed = FixedPoint(100)
    delta = predict_long(interactive_hyperdrive.interface, bonds=bonds_needed)
    event = agent.open_long(base=delta.user.base)
    _log_event("long ", "bonds", bonds_needed, event[0] if isinstance(event, list) else event)


def test_open_short_base(chain: Chain):
    """Demonstrate abililty to open short with base as input."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))

    base_needed = FixedPoint(100)
    delta = predict_short(interactive_hyperdrive.interface, base=base_needed)
    event = agent.open_short(bonds=delta.user.bonds)
    _log_event("short", "base ", base_needed, event[0] if isinstance(event, list) else event)
    _log_table(delta)


def predict_long(
    hyperdrive_interface: HyperdriveReadInterface,
    pool_state: PoolState | None = None,
    base: FixedPoint | None = None,
    bonds: FixedPoint | None = None,
    verbose: bool = False,
) -> TradeDeltas:
    """Predict the outcome of a long trade.

    Arguments
    ---------
    hyperdrive_interface: HyperdriveReadInterface
        Hyperdrive interface.
    pool_state: PoolState, optional
        The state of the pool, which includes block details, pool config, and pool info.
        If not given, use the current pool state.
    base: FixedPoint, optional
        The size of the long to open, in base. If not given, converted from bonds.
    bonds: FixedPoint, optional
        The size of the long to open, in bonds.
    verbose: bool
        Whether to print debug messages.

    Returns
    -------
    TradeDeltas
        The predicted deltas of base, bonds, and shares.

    """
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
        share_price_on_next_block = share_price * (
            FixedPoint(1) + hyperdrive_interface.get_variable_rate(pool_state.block_number) / FixedPoint(BLOCKS_IN_YEAR)
        )
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
    gov_scaling_factor = FixedPoint(1) - price_discount * curve_fee * governance_fee
    predicted_delta_base = base_needed * gov_scaling_factor
    predicted_delta_shares = base_needed / share_price * gov_scaling_factor
    if verbose:
        logging.info("predict_long(): predicted pool delta bonds is %s", predicted_delta_bonds)
        logging.info("predict_long(): predicted pool delta shares is %s", predicted_delta_shares)
        logging.info("predict_long(): predicted pool delta base is %s", predicted_delta_base)
    return TradeDeltas(
        user=Deltas(bonds=bonds_after_fees, base=base_needed, shares=base_needed / share_price),
        pool=Deltas(
            base=predicted_delta_base,
            shares=predicted_delta_shares,
            bonds=predicted_delta_bonds,
        ),
        fee=Deltas(
            bonds=bond_fees_to_pool,
            base=bond_fees_to_pool * spot_price,
            shares=bond_fees_to_pool * spot_price * share_price,
        ),
        governance=Deltas(
            bonds=bond_fees_to_gov,
            base=bond_fees_to_gov * spot_price,
            shares=bond_fees_to_gov * spot_price * share_price,
        ),
    )


def predict_short(
    hyperdrive_interface: HyperdriveReadInterface,
    pool_state: PoolState | None = None,
    base: FixedPoint | None = None,
    bonds: FixedPoint | None = None,
    verbose: bool = False,
) -> TradeDeltas:
    """Predict the outcome of a short trade.

    Arguments
    ---------
    hyperdrive_interface: HyperdriveReadInterface
        Hyperdrive interface.
    pool_state: PoolState, optional
        The state of the pool, which includes block details, pool config, and pool info.
        If not given, use the current pool state.
    base: FixedPoint, optional
        The size of the short to open, in base.
    bonds: FixedPoint, optional
        The size of the short to open, in bonds. If not given, bonds is calculated from base.
    verbose: bool
        Whether to print debug messages.

    Returns
    -------
    TradeDeltas
        The predicted deltas of base, bonds, and shares.
    """
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
        # this is the wrong direction for the swap, but we don't have the function in the other direction
        bonds_needed = hyperdrive_interface.calc_bonds_out_given_shares_in_down(base_needed / share_price)
        bonds_needed /= FixedPoint(1) - price_discount * curve_fee * (FixedPoint(1) - governance_fee)
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
        logging.info("predict_short(): predicted user delta shares is%s", shares_after_fees)
        logging.info("predict_short(): predicted fee delta base is %s", base_fees_to_pool)
        logging.info("predict_short(): predicted governance delta base is %s", base_fees_to_gov)
    predicted_delta_bonds = bonds_needed
    predicted_delta_shares = -shares_before_fees + base_fees_to_pool
    predicted_delta_base = predicted_delta_shares * share_price
    if verbose:
        logging.info("predict_short(): predicted pool delta bonds is %s", predicted_delta_bonds)
        logging.info("predict_short(): predicted pool delta shares is %s", predicted_delta_shares)
        logging.info("predict_short(): predicted pool delta base is %s", predicted_delta_base)
    return TradeDeltas(
        user=Deltas(bonds=bonds_needed, base=base_after_fees, shares=shares_after_fees),
        pool=Deltas(
            base=predicted_delta_base,
            shares=predicted_delta_shares,
            bonds=predicted_delta_bonds,
        ),
        fee=Deltas(
            bonds=base_fees_to_pool / spot_price,
            base=base_fees_to_pool,
            shares=base_fees_to_pool / share_price,
        ),
        governance=Deltas(
            bonds=base_fees_to_gov / spot_price,
            base=base_fees_to_gov,
            shares=base_fees_to_gov / share_price,
        ),
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
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))
    pool_state = deepcopy(hyperdrive_interface.current_pool_state)

    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    # convert from bonds to base, if needed
    bonds_needed = FixedPoint(100_000)
    shares_needed = hyperdrive_interface.calc_shares_in_given_bonds_out_up(bonds_needed)
    shares_needed /= FixedPoint(1) - price_discount * curve_fee
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    share_price_on_next_block = share_price * (
        FixedPoint(1) + hyperdrive_interface.get_variable_rate(pool_state.block_number) / FixedPoint(BLOCKS_IN_YEAR)
    )
    base_needed = shares_needed * share_price_on_next_block
    # use rust to predict trade outcome
    delta = predict_long(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed, verbose=True)

    # measure user wallet before trade
    user_base_before = agent.agent.wallet.balance.amount
    # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * pool_state_before.pool_info.vault_share_price
    # do the trade
    event = agent.open_long(base=base_needed)
    _log_event("long", "base", base_needed, event[0] if isinstance(event, list) else event)
    # measure pool after trade
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
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
    actual_delta_user_base = user_base_before - agent.agent.wallet.balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    assert abs(Decimal(str(actual_delta_user_base - base_needed))) < 1e-16
    actual_delta_user_bonds = list(agent.agent.wallet.longs.values())[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert abs(Decimal(str(actual_delta_user_bonds - bonds_needed))) < 1e-3

    bonds_discrepancy = Decimal(str((actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - delta.pool.shares) / delta.pool.shares))
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
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))

    base_needed = FixedPoint(100_000)
    delta = predict_long(hyperdrive_interface=hyperdrive_interface, base=base_needed, verbose=True)
    logging.info("bond_fees_to_pool is %s", delta.fee.bonds)
    logging.info("bond_fees_to_gov is %s", delta.governance.bonds)
    logging.info("predicted delta bonds is %s", delta.pool.bonds)
    logging.info("predicted delta shares is %s", delta.pool.shares)
    logging.info("predicted delta base is %s", delta.pool.base)

    # measure user wallet before trade
    user_base_before = agent.agent.wallet.balance.amount
    # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * pool_state_before.pool_info.vault_share_price
    # do the trade
    event = agent.open_long(base=base_needed)
    _log_event("long", "base", base_needed, event[0] if isinstance(event, list) else event)
    # measure pool's outcome after trade
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
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
    actual_delta_user_base = user_base_before - agent.agent.wallet.balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    assert abs(Decimal(str(actual_delta_user_base - base_needed))) < 1e-16

    bonds_discrepancy = Decimal(str((actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - delta.pool.shares) / delta.pool.bonds))
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy:e}")

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7


@pytest.mark.anvil
def test_predict_open_short_bonds(chain: Chain):
    """Predict outcome of an open short, for a given amount of bonds."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))

    bonds_needed = FixedPoint(100_000)
    delta = predict_short(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed, verbose=True)
    logging.info("predicted user delta shares is %s", delta.user.shares)
    logging.info("predicted fee delta base is %s", delta.fee.base)
    logging.info("predicted governance delta base is %s", delta.governance.base)
    logging.info("predicted pool delta bonds is %s", delta.pool.bonds)
    logging.info("predicted pool delta shares is %s", delta.pool.shares)
    logging.info("predicted pool delta base is %s", delta.pool.base)

    # measure user wallet before trade
    user_base_before = agent.agent.wallet.balance.amount
    # # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * pool_state_before.pool_info.vault_share_price
    # # do the trade
    event = agent.open_short(bonds=bonds_needed)
    _log_event("short", "bonds", bonds_needed, event[0] if isinstance(event, list) else event)
    # # measure pool after trade
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
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
    actual_delta_user_base = user_base_before - agent.agent.wallet.balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    actual_delta_user_bonds = list(agent.agent.wallet.shorts.values())[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert abs(Decimal(str(actual_delta_user_bonds - bonds_needed))) < 1e-3

    bonds_discrepancy = Decimal(str((actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - delta.pool.shares) / delta.pool.shares))
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy:e}")

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7


@pytest.mark.anvil
def test_predict_open_short_base(chain: Chain):
    """Predict outcome of an open short, for a given amount of base."""
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))

    # start with base_needed, convert to bonds_needed
    base_needed = FixedPoint(100_000)
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    # this is the wrong direction for the swap, but we don't have the function in the other direction
    bonds_needed = hyperdrive_interface.calc_bonds_out_given_shares_in_down(
        (base_needed / hyperdrive_interface.current_pool_state.pool_info.vault_share_price)
    )
    delta = predict_short(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed, verbose=True)
    logging.info("predicted user delta shares is%s", delta.user.shares)
    logging.info("predicted fee delta base is %s", delta.fee.base)
    logging.info("predicted governance delta base is %s", delta.governance.base)
    logging.info("predicted delta bonds is %s", delta.pool.bonds)
    logging.info("predicted delta shares is %s", delta.pool.shares)
    logging.info("predicted delta base is %s", delta.pool.base)

    # measure user wallet before trade
    user_base_before = agent.agent.wallet.balance.amount
    # # measure pool before trade
    pool_state_before = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_before = pool_state_before.pool_info.bond_reserves
    pool_shares_before = pool_state_before.pool_info.share_reserves
    pool_base_before = pool_shares_before * share_price
    # # do the trade
    event = agent.open_short(bonds=bonds_needed)
    _log_event("short", "bonds", bonds_needed, event[0] if isinstance(event, list) else event)
    # # measure pool after trade
    pool_state_after = deepcopy(hyperdrive_interface.current_pool_state)
    pool_bonds_after = pool_state_after.pool_info.bond_reserves
    pool_shares_after = pool_state_after.pool_info.share_reserves
    pool_base_after = pool_shares_after * pool_state_after.pool_info.vault_share_price
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
    actual_delta_user_base = user_base_before - agent.agent.wallet.balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    actual_delta_user_bonds = list(agent.agent.wallet.shorts.values())[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert abs(Decimal(str(actual_delta_user_bonds - bonds_needed))) < 1e-3

    bonds_discrepancy = Decimal(str((actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds))
    shares_discrepancy = Decimal(str((actual_delta_shares - delta.pool.shares) / delta.pool.shares))
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy:e}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy:e}")

    assert abs(bonds_discrepancy) < 1e-7
    assert abs(shares_discrepancy) < 1e-7
