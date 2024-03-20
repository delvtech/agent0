"""Tests of economic intuition."""

import logging
from copy import deepcopy

import pandas as pd
import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.utilities import predict_long, predict_short

YEAR_IN_SECONDS = 31_536_000

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

@pytest.mark.anvil
def test_discoverability(chain: LocalChain):
    """Test discoverability of rates across by time stretch."""
    liquidity = FixedPoint(10_000_000)
    time_stretch_apr_list = [0.03]
    with open("discoverability.csv", "w", encoding="UTF-8") as file:
        file.write("rate,time_stretch_apr\n")
        for time_stretch_apr in time_stretch_apr_list:
            interactive_config = LocalHyperdrive.Config(
                position_duration=YEAR_IN_SECONDS,  # 1 year term
                governance_lp_fee=FixedPoint(0.1),
                curve_fee=FixedPoint(0.01),
                flat_fee=FixedPoint(0),
                initial_liquidity=liquidity,
                initial_time_stretch_apr=FixedPoint(str(time_stretch_apr)),
            )
            interactive_hyperdrive = LocalHyperdrive(chain, interactive_config)
            interface = interactive_hyperdrive.interface

            max_long = interface.calc_max_long(liquidity)
            logging.info(f"Max long : base={float(max_long):>10,.0f}")
            max_short = interface.calc_max_short(liquidity)
            logging.info(f"Max short: base={float(max_short):>10,.0f}")
            biggest = int(max(max_long, max_short))
            increment = biggest // 10
            records = []
            for trade_size in range(increment, 11 * increment, increment):
                long_price = short_price = long_rate = short_rate = None
                if trade_size <= max_long:
                    long_trade = predict_long(interface, base=FixedPoint(trade_size))
                    pool_state = deepcopy(interface.current_pool_state)
                    pool_state.pool_info.bond_reserves += long_trade.pool.bonds
                    pool_state.pool_info.share_reserves += long_trade.pool.shares
                    long_price = interface.calc_spot_price(pool_state)
                    long_rate = interface.calc_fixed_rate(pool_state)
                if trade_size <= max_short:
                    short_trade = predict_short(interface, bonds=FixedPoint(trade_size))
                    pool_state = deepcopy(interface.current_pool_state)
                    pool_state.pool_info.bond_reserves += short_trade.pool.bonds
                    pool_state.pool_info.share_reserves += short_trade.pool.shares
                    short_price = interface.calc_spot_price(pool_state)
                    short_rate = interface.calc_fixed_rate(pool_state)
                records.append((trade_size, long_price, short_price, long_rate, short_rate))
            results_df = pd.DataFrame.from_records(records, columns=["trade_size", "long_price", "short_price", "long_rate", "short_rate"])
            logging.info(f"Prices:\n{results_df[['trade_size', 'long_price', 'short_price']]}")
            logging.info(f"Rates:\n{results_df[['trade_size', 'long_rate', 'short_rate']]}")

            # put all rates together in a discoverability vector
            rate_list = results_df["long_rate"].to_list() + results_df["short_rate"].to_list()
            discoverability = [float(num) if num is not None else None for num in rate_list]
            # remove None
            discoverability = [rate for rate in discoverability if rate is not None]
            # sort
            discoverability = sorted(discoverability)
            disc_df = pd.DataFrame(data=discoverability, columns=["discoverability"])
            disc_df["time_stretch_apr"] = time_stretch_apr
            disc_df.to_csv(file, mode="a", header=False, index=False)
            discoverability_text = '\n'.join([str(num) for num in discoverability])
            logging.info(f"Discoverability:{discoverability_text}")