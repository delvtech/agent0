"""Tests of economic intuition."""

import logging
import os
from copy import deepcopy
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.interactive.local_hyperdrive_agent import LocalHyperdriveAgent
from agent0.ethpy.hyperdrive.interface.read_write_interface import HyperdriveReadWriteInterface

YEAR_IN_SECONDS = 31_536_000

# too many local variables
# pylint: disable=too-many-locals
# too many statements
# pylint: disable=too-many-statements
# ruff: noqa: PLR0915
# I want to be able to use fancy f-string formatting
# pylint: disable=logging-fstring-interpolation


@pytest.mark.anvil
def test_symmetry(chain: LocalChain):
    """Check wether in equals out.

    One may be under the impression swaps between x and y have the same result, irrespective of direction.
    We set the number of bonds in and out to 100k and see if the resulting shares_in and shares_out differ.
    """
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(chain, interactive_config)
    interface = interactive_hyperdrive.interface
    shares_out = interface.calc_shares_out_given_bonds_in_down(FixedPoint(100_000))
    shares_in = interface.calc_shares_in_given_bonds_out_down(FixedPoint(100_000))
    print(shares_out)
    print(shares_in)
    assert shares_out != shares_in

def calc_price_and_rate(interface:HyperdriveReadWriteInterface):
    price = interface.calc_spot_price()
    rate = interface.calc_spot_rate()
    return price, rate

def trade(interface:HyperdriveReadWriteInterface, agent:LocalHyperdriveAgent, trade_portion, max_long, max_short):
    relevant_max = max_long if trade_portion > 0 else max_short
    trade_size = int(float(relevant_max) * trade_portion)
    trade_result = trade_long(interface, agent, trade_size) if trade_size > 0 else trade_short(interface, agent, abs(trade_size))
    return *trade_result, trade_size

def trade_long(interface:HyperdriveReadWriteInterface, agent:LocalHyperdriveAgent, trade_size):
    try:
        agent.open_long(base=FixedPoint(trade_size))
        return calc_price_and_rate(interface)
    except:
        pass
    return None, None

def trade_short(interface:HyperdriveReadWriteInterface, agent:LocalHyperdriveAgent, trade_size):
    try:
        agent.open_short(bonds=FixedPoint(trade_size))
        return calc_price_and_rate(interface)
    except:
        pass
    return None, None

def trade_liq(interface:HyperdriveReadWriteInterface, agent:LocalHyperdriveAgent, trade_size):
    agent.add_liquidity(base=trade_size)
    return calc_price_and_rate(interface)

# parametrize with time_stretch_apr
# TODO: add back 1% time_stretch_apr, currently failing in rust (https://github.com/delvtech/hyperdrive-rs/issues/62)
# @pytest.mark.parametrize("time_stretch_apr", [0.01, 0.05, 0.1, 0.2, 0.3])
@pytest.mark.parametrize(
    "trial,time_stretch_apr, trade_portion_one",
    [(1, 0.2, 0.90), (2, 0.2, 0.99)],
    # [(1, 0.2, 0.99)],
)
@pytest.mark.anvil
def test_discoverability(chain: LocalChain, trial: int, time_stretch_apr: float, trade_portion_one: float):
    """Test discoverability of rates by time stretch."""
    liquidity = FixedPoint(100)
    trade_portion_list = [*np.arange(0.1, 1.0, 0.1), 0.99]
    trade_portion_list += [-x for x in trade_portion_list]  # add negative portions
    records = []
    logging.info(f"Time stretch APR: {time_stretch_apr}")
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
        initial_liquidity=liquidity,
        initial_fixed_apr=FixedPoint(time_stretch_apr),
        initial_time_stretch_apr=FixedPoint(time_stretch_apr),
        factory_min_fixed_apr=FixedPoint(0.001),
        factory_max_fixed_apr=FixedPoint(1000),
        factory_min_time_stretch_apr=FixedPoint(0.001),
        factory_max_time_stretch_apr=FixedPoint(1000),
    )
    hyperdrive:LocalHyperdrive = LocalHyperdrive(chain, interactive_config)
    agent:LocalHyperdriveAgent = hyperdrive.init_agent(base=FixedPoint(1e18))
    interface = hyperdrive.interface
    time_stretch = interface.current_pool_state.pool_config.time_stretch
    logging.info("Time stretch: %s", time_stretch)
    logging.info("Time stretch: %s", time_stretch)

    max_long = interface.calc_max_long(budget=agent.wallet.balance.amount)
    max_short = interface.calc_max_short(budget=agent.wallet.balance.amount)
    logging.info(f"Max long :  base={float(max_long):>10,.0f}")
    logging.info(f"Max short: bonds={float(max_short):>10,.0f}")
    price, rate, trade_size = trade(interface, agent, trade_portion_one, max_long, max_short)
    records.append((trial, "first", interface.calc_effective_share_reserves(), trade_size, trade_portion_one, price, rate, time_stretch_apr))
    price, rate = trade_liq(interface, agent, liquidity)
    records.append((trial, "addliq", interface.calc_effective_share_reserves(), trade_size, trade_portion_one, price, rate, time_stretch_apr))
    del price, rate, trade_size

    # save the snapshot
    chain.save_snapshot()

    # then we short
    max_short_two = interface.calc_max_short(budget=agent.wallet.balance.amount)
    max_long_two = interface.calc_max_long(budget=agent.wallet.balance.amount)
    logging.info(f"Max short: bonds={float(max_short_two):>10,.0f}")
    logging.info(f"Max long :  base={float(max_long_two):>10,.0f}")
    for trade_portion_two in trade_portion_list:
        chain.load_snapshot()
        price, rate, trade_size = trade(interface, agent, trade_portion_two, max_long_two, max_short_two)
        records.append((trial, "second", interface.calc_effective_share_reserves(), trade_size, trade_portion_two, price, rate, time_stretch_apr))
        logging.info("trade_portion=%s, rate=%s", trade_portion_two, rate)
    columns = ["trial", "type", "liquidity", "trade_size", "portion", "price", "rate", "time_stretch_apr"]
    new_result = pd.DataFrame.from_records(records, columns=columns)
    logging.info(f"\n{new_result[columns[:-1]]}")
    previous_results = pd.read_csv("discoverability.csv") if os.path.exists("discoverability.csv") else pd.DataFrame()
    logging.info(f"previous_results.shape: {previous_results.shape}")
    all_results = pd.concat([previous_results, new_result], ignore_index=True, axis=0)
    logging.info(f"all_results.shape: {all_results.shape}")
    all_results.to_csv("discoverability.csv", index=False)


@pytest.mark.anvil
def test_lp_pnl(chain: LocalChain):
    """Test whether LP PNL matches our rule of thumb."""
    liquidity = FixedPoint(10_000_000)
    time_stretch_apr_list = [0.05]
    with open("discoverability.csv", "w", encoding="UTF-8") as file:
        file.write("trade_size,rate,time_stretch_apr\n")
        for time_stretch_apr in time_stretch_apr_list:
            logging.info(f"Time stretch APR: {time_stretch_apr}")
            interactive_config = LocalHyperdrive.Config(
                position_duration=YEAR_IN_SECONDS,  # 1 year term
                governance_lp_fee=FixedPoint(0.1),  # 10% governance fee
                curve_fee=FixedPoint(0.01),  # 1% curve fee
                flat_fee=FixedPoint(0),  # 0bps flat fee
                initial_liquidity=liquidity,
                initial_time_stretch_apr=FixedPoint(str(time_stretch_apr)),
            )
            interactive_hyperdrive = LocalHyperdrive(chain, interactive_config)
            interface = interactive_hyperdrive.interface

            manual_agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e9))
            manual_agent.open_short(bonds=FixedPoint(9_050_000))
            logging.info(f"New rate: {interface.calc_spot_rate()}")


def test_lp_pnl_calculator(chain: LocalChain):
    """Calculate LP PNL given a set of parameters."""
    initial_liquidity = FixedPoint(10_000_000)
    time_stretch_apr = 0.05
    initial_fixed_apr = 0.05

    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0),
        flat_fee=FixedPoint(0),
        initial_liquidity=initial_liquidity,
        initial_time_stretch_apr=FixedPoint(str(time_stretch_apr)),
        calc_pnl=False,
        initial_fixed_apr=FixedPoint(str(initial_fixed_apr)),
        initial_variable_rate=FixedPoint(str(initial_fixed_apr)),
    )
    max_short = LocalHyperdrive(chain, interactive_config).interface.calc_max_short(budget=FixedPoint(1e12))
    increment = int(max_short) // 10
    records = []
    for trade_size in range(increment, 11 * increment, increment):
        interactive_config = LocalHyperdrive.Config(
            position_duration=YEAR_IN_SECONDS,  # 1 year term
            governance_lp_fee=FixedPoint(0.1),
            curve_fee=FixedPoint(0),
            flat_fee=FixedPoint(0),
            initial_liquidity=initial_liquidity,
            initial_time_stretch_apr=FixedPoint(str(time_stretch_apr)),
            calc_pnl=False,
            initial_fixed_apr=FixedPoint(str(initial_fixed_apr)),
            initial_variable_rate=FixedPoint(str(initial_fixed_apr)),
        )
        interactive_hyperdrive = LocalHyperdrive(chain, interactive_config)
        lp_larry = interactive_hyperdrive.init_agent(
            base=FixedPoint(0), name="larry", private_key=chain.get_deployer_account_private_key()
        )
        manual_agent = interactive_hyperdrive.init_agent(base=FixedPoint(1e12))
        start_timestamp = interactive_hyperdrive.interface.current_pool_state.block_time

        print("\n=== START ===")
        starting_base = {}
        for agent in interactive_hyperdrive._pool_agents:  # pylint: disable=protected-access
            if agent.name == "larry":
                # larry is the deployer, their base balance is the initial liquidity
                starting_base[agent.name] = initial_liquidity
            else:
                starting_base[agent.name] = agent.wallet.balance.amount
        for k, v in starting_base.items():
            if k is not None:
                print(f"{k:6}: {float(v):>17,.0f}")
        pool_state = deepcopy(interactive_hyperdrive.interface.current_pool_state)
        print("fixed rate is", interactive_hyperdrive.interface.calc_spot_rate(pool_state))
        print(f"lp_share_price={pool_state.pool_info.lp_share_price}")

        print(f"=== TRADE ({trade_size:,.0f}) ===")
        short_bonds = interactive_hyperdrive.interface.calc_shares_out_given_bonds_in_down(FixedPoint(trade_size))
        event_list = manual_agent.open_short(bonds=short_bonds)
        event = event_list[0] if isinstance(event_list, list) else event_list
        effective_spot_price = event.base_proceeds / event.bond_amount
        effective_interest_rate = (FixedPoint(1) - effective_spot_price) / effective_spot_price
        position_size = manual_agent.agent.wallet.shorts[list(manual_agent.agent.wallet.shorts)[0]].balance
        print(f"  position size is {float(position_size):,.0f} bonds")
        spent_base = {}
        for agent in interactive_hyperdrive._pool_agents:  # pylint: disable=protected-access
            spent_base[agent.name] = starting_base[agent.name] - agent.wallet.balance.amount
        ending_pool_state = deepcopy(interactive_hyperdrive.interface.current_pool_state)
        new_fixed_rate = interactive_hyperdrive.interface.calc_spot_rate(ending_pool_state)
        print("fixed rate is", new_fixed_rate)
        print(f"lp_share_price={ending_pool_state.pool_info.lp_share_price}")
        # set variable rate equal to fixed rate
        interactive_hyperdrive.set_variable_rate(new_fixed_rate)

        # advance one year to let all positions mature
        current_timestamp = interactive_hyperdrive.interface.current_pool_state.block_time
        time_already_passed = current_timestamp - start_timestamp
        advance_time_to = YEAR_IN_SECONDS
        advance_time_seconds = int(advance_time_to) - time_already_passed
        print(f"  advancing {advance_time_seconds} seconds... ", end="")
        chain.advance_time(advance_time_seconds, create_checkpoints=False)
        print("done.")
        current_timestamp = interactive_hyperdrive.interface.current_pool_state.block_time
        print(f"new timestamp is {current_timestamp}")
        # close all positions
        print("before agent action")
        for short in manual_agent.agent.wallet.shorts:
            print(
                f"  {short}: time to maturity {short-current_timestamp} seconds ({(short-current_timestamp)/YEAR_IN_SECONDS:0.5f} years)"
            )
        manual_agent.liquidate()
        print("after  agent action")
        for short in manual_agent.agent.wallet.shorts:
            print(
                f"  {short}: time to maturity {short-current_timestamp} seconds ({(short-current_timestamp)/YEAR_IN_SECONDS:0.5f} years)"
            )
        lp_larry.remove_liquidity(lp_larry.wallet.lp_tokens - interactive_config.minimum_share_reserves * 2)

        print("=== END ===")
        print("ending WETH balances:")
        ending_base = {}
        for agent in interactive_hyperdrive._pool_agents:  # pylint: disable=protected-access
            ending_base[agent.name] = agent.wallet.balance.amount
        for k, v in ending_base.items():
            if k is not None:
                print(f"  {k:6}: {float(v):>17,.0f}")
        lp_larry_starting_base = starting_base["larry"]
        lp_larry_ending_base = ending_base["larry"]
        lp_larry_return_abs = lp_larry_ending_base - lp_larry_starting_base
        lp_larry_return_pct = lp_larry_return_abs / lp_larry_starting_base
        ending_pool_state = deepcopy(interactive_hyperdrive.interface.current_pool_state)
        print("fixed rate is", interactive_hyperdrive.interface.calc_spot_rate(ending_pool_state))
        print(f"lp_share_price={ending_pool_state.pool_info.lp_share_price}")
        print("returns:")
        # calculate rule of thumb return
        linear_interest_rate = (new_fixed_rate - FixedPoint(initial_fixed_apr)) / FixedPoint(2) + FixedPoint(
            initial_fixed_apr
        )
        # estimated_arb_return = position_size * (new_fixed_rate - FixedPoint(initial_fixed_apr)) / FixedPoint(2)
        estimated_arb_return = position_size * (new_fixed_rate - FixedPoint(effective_interest_rate))
        print(f"estimate arb return is {float(estimated_arb_return):>17,.0f}")
        estimated_lp_return = lp_larry_starting_base * new_fixed_rate - estimated_arb_return
        # estimated_lp_return_pct = estimated_lp_return / lp_larry_starting_base
        estimated_lp_return_pct_linear = (
            new_fixed_rate - (new_fixed_rate - FixedPoint(linear_interest_rate)) * event.bond_amount / initial_liquidity
        )
        estimated_lp_return_pct_effective = (
            new_fixed_rate
            - (new_fixed_rate - FixedPoint(effective_interest_rate)) * event.base_proceeds / initial_liquidity
        )
        print(f"estimated LP return is {float(estimated_lp_return):>17,.0f}")
        print(f"actual    LP return is {float(lp_larry_return_abs):>17,.0f}")
        print(f"estimated LP return is {float(estimated_lp_return_pct_effective)*100:>17,.5f}% (effective)")
        print(f"estimated LP return is {float(estimated_lp_return_pct_linear)*100:>17,.5f}% (linear)")
        print(f"actual    LP return is {float(lp_larry_return_pct)*100:>17,.5f}%")
        return_diff = estimated_lp_return_pct_effective - lp_larry_return_pct
        return_diff_pct = return_diff / lp_larry_return_pct
        print(f"  error is {float(return_diff)*100:>17,.5f}% points")
        print(f"  error is {float(return_diff_pct*100):>17,.5f}%")
        pool_info = interactive_hyperdrive.get_pool_state()
        time_passed_days = (pool_info.timestamp.iloc[-1] - pool_info.timestamp.iloc[0]).total_seconds() / 60 / 60 / 24
        print(f"  Holding Period Return: {float(lp_larry_return_abs):,.0f} ({float(lp_larry_return_pct):,.2%})")
        print(f"    Holding Period: {time_passed_days:,.2f} days")
        years_passed = time_passed_days / 365
        print(f"    Annualization Factor = {years_passed:,.5f} years passed ({time_passed_days:.2f}/365)")
        print(f"    APR = (1+HPR) ** (1/{years_passed:,.5f}) - 1")
        apr = (1 + Decimal(str(lp_larry_return_pct))) ** (1 / Decimal(years_passed)) - 1
        print(f"    Annualized Percent Return: {apr:,.2%}")

        records.append(
            (
                new_fixed_rate,
                estimated_lp_return_pct_effective,
                estimated_lp_return_pct_linear,
                lp_larry_return_pct,
                return_diff,
                return_diff_pct,
                effective_interest_rate,
                linear_interest_rate,
            )
        )

    df = pd.DataFrame(
        records,
        columns=[
            "new_fixed_rate",
            "estimated_lp_return_pct_effective",
            "estimated_lp_return_pct_linear",
            "actual_lp_return_pct",
            "return_diff",
            "return_diff_pct",
            "effective_interest_rate",
            "linear_interest_rate",
        ],
    )
    print(df)
    df.to_csv("lp_returns.csv", index=False)
