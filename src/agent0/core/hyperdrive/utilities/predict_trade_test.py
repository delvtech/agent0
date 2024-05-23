"""Test our ability to predict the outcome of a trade.

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

import pytest
from fixedpointmath import FixedPoint, isclose
from tabulate import tabulate

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.core.hyperdrive.utilities.predict import TradeDeltas, predict_long, predict_short

# it's just a test
# pylint: disable=logging-fstring-interpolation
# pylint: disable=too-many-locals
# allow magic value comparison (like < 1e-16)
# ruff: noqa: PLR2004
# allow lots of statements
# ruff: noqa: PLR0915

YEAR_IN_SECONDS = 31_536_000
YEAR_IN_BLOCKS = YEAR_IN_SECONDS / 12


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
    assert event.as_base
    logging.info(
        "opened %s with input %s=%s, output Δbonds= %s%s, Δbase= %s%s",
        trade_type,
        input_type,
        base_needed,
        "+" if event.bond_amount > 0 else "",
        event.bond_amount,
        "+" if event.amount > 0 else "",
        event.amount,
    )


def test_prediction_example(fast_chain_fixture: LocalChain):
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
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    agent = fast_chain_fixture.init_agent(base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive)
    base_needed = FixedPoint(100)
    delta = predict_long(hyperdrive_interface=interactive_hyperdrive.interface, base=base_needed)
    event = agent.open_long(base=base_needed)
    _log_event("long", "base", base_needed, event[0] if isinstance(event, list) else event)
    _log_table(delta)


def test_open_long_bonds(fast_chain_fixture: LocalChain):
    """Demonstrate abililty to open long with bonds as input."""
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    agent = fast_chain_fixture.init_agent(base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive)

    bonds_needed = FixedPoint(100)
    delta = predict_long(interactive_hyperdrive.interface, bonds=bonds_needed)
    event = agent.open_long(base=delta.user.base)
    _log_event("long ", "bonds", bonds_needed, event[0] if isinstance(event, list) else event)


def test_open_short_base(fast_chain_fixture: LocalChain):
    """Demonstrate abililty to open short with base as input."""
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    agent = fast_chain_fixture.init_agent(base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive)

    base_needed = FixedPoint(100)
    delta = predict_short(interactive_hyperdrive.interface, base=base_needed)
    event = agent.open_short(bonds=delta.user.bonds)
    _log_event("short", "base ", base_needed, event[0] if isinstance(event, list) else event)
    _log_table(delta)


@pytest.mark.anvil
def test_predict_open_long_bonds(fast_chain_fixture: LocalChain):
    """Predict outcome of an open long, for a given amount of bonds."""
    # setup
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    agent = fast_chain_fixture.init_agent(base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive)
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
        FixedPoint(1) + hyperdrive_interface.get_variable_rate(pool_state.block_number) / FixedPoint(YEAR_IN_BLOCKS)
    )
    base_needed = shares_needed * share_price_on_next_block
    # use rust to predict trade outcome
    delta = predict_long(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed)

    # measure user wallet before trade
    user_base_before = agent.get_wallet().balance.amount
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
    assert isclose(delta.user.base, base_needed, abs_tol=FixedPoint("1e-16"))
    # does the actual outcome match the prediction
    actual_delta_user_base = user_base_before - agent.get_wallet().balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    assert isclose(actual_delta_user_base, base_needed, abs_tol=FixedPoint("1e-16"))
    actual_delta_user_bonds = agent.get_longs()[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    # TODO fix tolerance
    # https://github.com/delvtech/agent0/issues/1357
    assert isclose(actual_delta_user_bonds, bonds_needed, abs_tol=FixedPoint("1e-2"))

    bonds_discrepancy = (actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds
    shares_discrepancy = (actual_delta_shares - delta.pool.shares) / delta.pool.shares
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy}")

    assert abs(bonds_discrepancy) < FixedPoint("1e-4")
    assert abs(shares_discrepancy) < FixedPoint("1e-7")


@pytest.mark.anvil
def test_predict_open_long_base(fast_chain_fixture: LocalChain):
    """Predict outcome of an open long, for a given amount of base."""
    # setup
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    agent = fast_chain_fixture.init_agent(base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive)

    base_needed = FixedPoint(100_000)
    delta = predict_long(hyperdrive_interface=hyperdrive_interface, base=base_needed)
    logging.info("bond_fees_to_pool is %s", delta.fee.bonds)
    logging.info("bond_fees_to_gov is %s", delta.governance.bonds)
    logging.info("predicted delta bonds is %s", delta.pool.bonds)
    logging.info("predicted delta shares is %s", delta.pool.shares)
    logging.info("predicted delta base is %s", delta.pool.base)

    # measure user wallet before trade
    user_base_before = agent.get_wallet().balance.amount
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
    assert isclose(delta.user.base, base_needed, abs_tol=FixedPoint("1e-16"))
    # does the actual outcome match the prediction
    actual_delta_user_base = user_base_before - agent.get_wallet().balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    assert isclose(actual_delta_user_base, base_needed, abs_tol=FixedPoint("1e-16"))

    bonds_discrepancy = (actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds
    shares_discrepancy = (actual_delta_shares - delta.pool.shares) / delta.pool.bonds
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy}")

    assert abs(bonds_discrepancy) < FixedPoint("1e-7")
    assert abs(shares_discrepancy) < FixedPoint("1e-7")


@pytest.mark.anvil
def test_predict_open_short_bonds(fast_chain_fixture: LocalChain):
    """Predict outcome of an open short, for a given amount of bonds."""
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    agent = fast_chain_fixture.init_agent(base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive)

    bonds_needed = FixedPoint(100_000)
    delta = predict_short(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed)
    logging.info("predicted user delta shares is %s", delta.user.shares)
    logging.info("predicted fee delta base is %s", delta.fee.base)
    logging.info("predicted governance delta base is %s", delta.governance.base)
    logging.info("predicted pool delta bonds is %s", delta.pool.bonds)
    logging.info("predicted pool delta shares is %s", delta.pool.shares)
    logging.info("predicted pool delta base is %s", delta.pool.base)

    # measure user wallet before trade
    user_base_before = agent.get_wallet().balance.amount
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
    assert isclose(delta.user.bonds, bonds_needed, abs_tol=FixedPoint("1e-16"))
    # does the actual outcome match the prediction
    actual_delta_user_base = user_base_before - agent.get_wallet().balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    actual_delta_user_bonds = agent.get_shorts()[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert isclose(actual_delta_user_bonds, bonds_needed, abs_tol=FixedPoint("1e-3"))

    bonds_discrepancy = (actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds
    shares_discrepancy = (actual_delta_shares - delta.pool.shares) / delta.pool.shares
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy}")

    assert abs(bonds_discrepancy) < FixedPoint("1e-7")
    assert abs(shares_discrepancy) < FixedPoint("1e-7")


@pytest.mark.anvil
def test_predict_open_short_base(fast_chain_fixture: LocalChain):
    """Predict outcome of an open short, for a given amount of base."""
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    hyperdrive_interface = interactive_hyperdrive.interface
    agent = fast_chain_fixture.init_agent(base=FixedPoint(1e9), eth=FixedPoint(10), pool=interactive_hyperdrive)

    # start with base_needed, convert to bonds_needed
    base_needed = FixedPoint(100_000)
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    # this is the wrong direction for the swap, but we don't have the function in the other direction
    bonds_needed = hyperdrive_interface.calc_bonds_out_given_shares_in_down(
        (base_needed / hyperdrive_interface.current_pool_state.pool_info.vault_share_price)
    )
    delta = predict_short(hyperdrive_interface=hyperdrive_interface, bonds=bonds_needed)
    logging.info("predicted user delta shares is%s", delta.user.shares)
    logging.info("predicted fee delta base is %s", delta.fee.base)
    logging.info("predicted governance delta base is %s", delta.governance.base)
    logging.info("predicted delta bonds is %s", delta.pool.bonds)
    logging.info("predicted delta shares is %s", delta.pool.shares)
    logging.info("predicted delta base is %s", delta.pool.base)

    # measure user wallet before trade
    user_base_before = agent.get_wallet().balance.amount
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
    assert isclose(delta.user.bonds, bonds_needed, abs_tol=FixedPoint("1e-16"))
    # does the actual outcome match the prediction
    actual_delta_user_base = user_base_before - agent.get_wallet().balance.amount
    logging.info("actual user delta base is %s", actual_delta_user_base)
    actual_delta_user_bonds = agent.get_shorts()[0].balance
    logging.info("actual user delta bonds is %s", actual_delta_user_bonds)
    assert isclose(actual_delta_user_bonds, bonds_needed, abs_tol=FixedPoint("1e-3"))

    bonds_discrepancy = (actual_delta_bonds - delta.pool.bonds) / delta.pool.bonds
    shares_discrepancy = (actual_delta_shares - delta.pool.shares) / delta.pool.shares
    logging.info(f"discrepancy (%) for bonds is {bonds_discrepancy}")
    logging.info(f"discrepancy (%) for shares is {shares_discrepancy}")

    assert abs(bonds_discrepancy) < FixedPoint("1e-7")
    assert abs(shares_discrepancy) < FixedPoint("1e-7")
