"""Test the ability of bots to hit a target rate."""
from __future__ import annotations

import logging

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import LocalChain, InteractiveHyperdrive
from agent0.hyperdrive.policies.zoo import Zoo
from agent0.hyperdrive.interactive.event_types import CloseLong, CloseShort

TRADE_AMOUNTS = [0.003, 1e5, 2e5]  # 0.003 is three times the minimum transaction amount of local test deploy
# We hit the target rate to the 5th decimal of precision.
# That means 0.050001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-5)
YEAR_IN_SECONDS = 31_536_000


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_long(chain: LocalChain, trade_amount: float):
    """Open a long to hit the target rate."""
    interactive_config = InteractiveHyperdrive.Config()
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)

    # create arbitrage andy
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    andy = interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )

    # change the fixed rate
    interactive_hyperdrive.init_agent(base=FixedPoint(1e9)).open_short(bonds=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back
    andy.execute_policy_action()

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
def test_open_short(chain: LocalChain, trade_amount: float):
    """Open a short to hit the target rate."""
    interactive_config = InteractiveHyperdrive.Config()
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)

    # create arbitrage andy
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    andy = interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )

    # change the fixed rate
    interactive_hyperdrive.init_agent(base=FixedPoint(1e9)).open_long(base=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back
    andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION

@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", [1e7])
def test_close_long(chain: LocalChain, trade_amount: float):
    """Close a long to hit the target rate."""
    interactive_config = InteractiveHyperdrive.Config(position_duration=YEAR_IN_SECONDS, governance_lp_fee=FixedPoint(0))
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)

    # create arbitrage andy
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    andy = interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )
    # create manual agent
    manual_agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # give andy a long position
    pool_bonds_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    event = andy.open_long(base=FixedPoint(trade_amount))
    pool_bonds_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    d_bonds = pool_bonds_after - pool_bonds_before  # instead of event.bond_amount
    d_shares = pool_shares_after - pool_shares_before  # instead of event.base_amount
    d_time = block_time_after - block_time_before
    logging.warning("Andy opened long %s base.", trade_amount)
    logging.warning("Δtime=%s", d_time)
    logging.warning(" pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares)
    logging.warning(" event Δbonds= %s%s, Δbase= %s%s", "+" if event.bond_amount > 0 else "", event.bond_amount, "+" if event.base_amount > 0 else "", event.base_amount)
    # undo this trade manually
    manual_agent.open_short(bonds=FixedPoint(event.bond_amount))

    # change the fixed rate
    manual_agent.open_long(base=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.warning("intermediate fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # pass time
    chain.advance_time(YEAR_IN_SECONDS / 2, create_checkpoints=False)

    # arbitrage it back
    event_list = andy.execute_policy_action()
    logging.warning("andy executed %s", event_list)
    event = event_list[0] if isinstance(event_list, list) else event_list
    assert isinstance(event, CloseLong)

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION

@pytest.mark.anvil
# @pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
@pytest.mark.parametrize("trade_amount", [1e3])
def test_close_short(chain: LocalChain, trade_amount: float):
    """Close a short to hit the target rate."""
    interactive_config = InteractiveHyperdrive.Config(position_duration=31_536_000)  # 1 year term
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)

    # create arbitrage andy
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    andy = interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )
    # create manual agent
    manual_agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # give andy a short position twice the trade amount, to be sufficiently large when closing
    pool_bonds_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_before = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    event = andy.open_short(bonds=FixedPoint(350*trade_amount))
    # chain.advance_time(12)
    pool_bonds_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.bond_reserves
    pool_shares_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_reserves
    block_time_after = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    d_bonds = pool_bonds_after - pool_bonds_before  # instead of event.bond_amount
    d_shares = pool_shares_after - pool_shares_before  # instead of event.base_amount
    d_time = block_time_after - block_time_before
    logging.warning("Andy opened short %s bonds.", 350*trade_amount)
    logging.warning("Δtime=%s", d_time)
    logging.warning(" pool  Δbonds= %s%s, Δbase= %s%s", "+" if d_bonds > 0 else "", d_bonds, "+" if d_shares > 0 else "", d_shares)
    logging.warning(" event Δbonds= %s%s, Δbase= %s%s", "+" if event.bond_amount > 0 else "", event.bond_amount, "+" if event.base_amount > 0 else "", event.base_amount)
    # undo this trade manually
    event = manual_agent.open_long(base=FixedPoint(event.base_amount))
    logging.warning("manually opened long, bonds=%s, base=%s", event.bond_amount, event.base_amount)

    # change the fixed rate
    event = manual_agent.open_short(bonds=FixedPoint(trade_amount))
    logging.warning("manually opened long, bonds=%s, base=%s", event.bond_amount, event.base_amount)

    # report fixed rate
    logging.warning("intermediate fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back
    event_list = andy.execute_policy_action()
    logging.warning("andy executed %s", event_list)
    event = event_list[0] if isinstance(event_list, list) else event_list
    assert isinstance(event, CloseShort)
    logging.warning("Andy closed short, bonds=%s, base=%s", event.bond_amount, event.base_amount)

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION

@pytest.mark.anvil
def test_already_at_target(chain: LocalChain):
    """Already at target, do nothing."""
    interactive_config = InteractiveHyperdrive.Config()
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)

    # create arbitrage andy
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    andy = interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back
    andy.execute_policy_action()

    # report results
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION
