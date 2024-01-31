"""Test the ability of bots to hit a target rate."""

from __future__ import annotations

import logging
from copy import deepcopy

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive
from agent0.hyperdrive.interactive.chain import Chain
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.policies.zoo import Zoo

# avoid unnecessary warning from using fixtures defined in outer scope
# pylint: disable=redefined-outer-name

TRADE_AMOUNTS = [0.003, 1e4, 1e5]  # 0.003 is three times the minimum transaction amount of local test deploy
# We hit the target rate to the 5th decimal of precision.
# That means 0.050001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-5)
YEAR_IN_SECONDS = 31_536_000

# pylint: disable=missing-function-docstring,too-many-statements,logging-fstring-interpolation,missing-return-type-doc
# pylint: disable=missing-return-doc,too-many-function-args


def create_arbitrage_andy(
    interactive_hyperdrive, base_budget: FixedPoint = FixedPoint(1e9)
) -> InteractiveHyperdriveAgent:
    """Create Arbitrage Andy interactive hyperdrive agent used to arbitrage the fixed rate to the variable rate.

    Arguments
    ---------
    interactive_hyperdrive: InteractiveHyperdrive
        Interactive hyperdrive.
    base_budget: FixedPoint
        The budget given to Arbitrage Andy, in base.

    Returns
    -------
    InteractiveHyperdriveAgent
        Arbitrage Andy interactive hyperdrive agent."""
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.interface.pool_config.minimum_transaction_amount,
    )
    return interactive_hyperdrive.init_agent(
        base=base_budget, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )


@pytest.mark.anvil
def test_lp_return(chain: Chain):
    """Predict LP return."""
    initial_liquidity = FixedPoint(2 * 10**8)  # 20 million
    daily_volume_percentage_of_liquidity = FixedPoint(0.05)
    # base_amount_to_open = initial_liquidity * daily_volume_percentage_of_liquidity // 2  # arbitrage will double this
    interactive_config = InteractiveHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
        initial_liquidity=initial_liquidity,
        calc_pnl=False,
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    deployer_privkey = chain.get_deployer_account_private_key()
    lp_larry = interactive_hyperdrive.init_agent(base=FixedPoint(100_000), name="larry", private_key=deployer_privkey)
    agent_budget_base = FixedPoint(1e12)
    arbitrage_andy = create_arbitrage_andy(interactive_hyperdrive=interactive_hyperdrive, base_budget=agent_budget_base)
    manual_agent = interactive_hyperdrive.init_agent(base=agent_budget_base)
    max_long_base = interactive_hyperdrive.interface.calc_max_long(budget=manual_agent.wallet.balance.amount)
    number_of_trades = int(initial_liquidity * daily_volume_percentage_of_liquidity // 2 * 365 // max_long_base)

    # print pool condition before any trades
    pool_state = deepcopy(interactive_hyperdrive.interface.current_pool_state)
    starting_bond_reserves = pool_state.pool_info.bond_reserves
    starting_share_reserves = pool_state.pool_info.share_reserves
    starting_price = interactive_hyperdrive.interface.calc_spot_price(pool_state)
    starting_fixed_rate = interactive_hyperdrive.interface.calc_fixed_rate(pool_state)
    print("starting bond_reserves is", starting_bond_reserves)
    print("starting share_reserves is", starting_share_reserves)
    print("starting spot price is", starting_price)
    print("starting fixed rate is", starting_fixed_rate)

    print("=== STARTING WETH BALANCES ===")
    starting_base = {}
    for agent in interactive_hyperdrive._pool_agents:  # pylint: disable=protected-access
        starting_base[agent.name] = agent.wallet.balance.amount
    for k, v in starting_base.items():
        if k is not None:
            print(f"{k:6}: {float(v):13,.0f}")

    # do trades
    print(f"attempting {number_of_trades} trades of {max_long_base} base")
    for _ in range(number_of_trades):
        manual_agent.open_long(base=max_long_base)
        event_list = arbitrage_andy.execute_policy_action()
    # advance one year to let all positions mature
    chain.advance_time(YEAR_IN_SECONDS, create_checkpoints=False)
    # close all positions
    events = manual_agent.liquidate()
    for event in events:
        print(event)
    event_list = arbitrage_andy.execute_policy_action()
    for event in event_list:
        print(event)
    lp_larry.remove_liquidity(lp_larry.wallet.lp_tokens - interactive_config.minimum_share_reserves * 2)

    print("=== ENDING WETH BALANCES ===")
    ending_base = {}
    for agent in interactive_hyperdrive._pool_agents:  # pylint: disable=protected-access
        ending_base[agent.name] = agent.wallet.balance.amount
    for k, v in ending_base.items():
        if k is not None:
            print(f"{k:6}: {float(v):13,.0f}")

    # display pool condition after all trades
    ending_pool_state = deepcopy(interactive_hyperdrive.interface.current_pool_state)
    ending_bond_reserves = ending_pool_state.pool_info.bond_reserves
    ending_share_reserves = ending_pool_state.pool_info.share_reserves
    ending_price = interactive_hyperdrive.interface.calc_spot_price(ending_pool_state)
    ending_fixed_rate = interactive_hyperdrive.interface.calc_fixed_rate(ending_pool_state)
    print("ending bond_reserves is", ending_bond_reserves)
    print("ending share_reserves is", ending_share_reserves)
    print("ending spot price is", ending_price)
    print("ending fixed rate is", ending_fixed_rate)
