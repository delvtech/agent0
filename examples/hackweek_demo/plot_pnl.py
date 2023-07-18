"""Plots the pnl"""
from __future__ import annotations

from typing import NamedTuple

import pandas as pd
from extract_data_logs import calculate_spot_price
from fixedpointmath import FixedPoint
from matplotlib import ticker as mpl_ticker

import elfpy
from elfpy import types
from elfpy.data import postgres
from elfpy.wallet.wallet import Long, Short, Wallet


def get_wallet_from_onchain_trade_info(
    address: str,
    trades: pd.DataFrame,
    index: int = 0,
    add_to_existing_wallet: Wallet | None = None,
) -> Wallet:
    # pylint: disable=too-many-arguments, too-many-branches, too-many-locals
    r"""Construct wallet balances from on-chain trade info.

    Arguments
     ---------
     address : str
         Address of the wallet.
     info : OnChainTradeInfo
         On-chain trade info.
     index : int
         Index of the wallet among ALL agents.

     Returns
     -------
     Wallet
         Wallet with Short, Long, and LP positions.
    """
    share_price = trades.share_price

    # TODO: remove restriction forcing Wallet index to be an int (issue #415)
    if add_to_existing_wallet is None:
        wallet = Wallet(
            address=index,
            balance=types.Quantity(amount=FixedPoint(scaled_value=0), unit=types.TokenType.BASE),
        )
    else:
        wallet = add_to_existing_wallet

    position_id = trades["id"]
    trades_in_position = ((trades["from"] == address) | (trades["to"] == address)) & (trades["id"] == position_id)

    positive_balance = int(trades.loc[(trades_in_position) & (trades["to"] == address), "value"].sum())
    negative_balance = int(trades.loc[(trades_in_position) & (trades["from"] == address), "value"].sum())
    balance = positive_balance - negative_balance

    asset_type = trades["trade_enum"].iloc[0]
    maturity = trades["maturity_time"].iloc[0]
    mint_time = int(maturity) - elfpy.SECONDS_IN_YEAR

    # check if there's an outstanding balance
    if balance != 0:
        if asset_type == "SHORT":
            # loop across all the positions owned by this wallet
            sum_product_of_open_share_price_and_value, sum_value = 0, 0

            # WEIGHTED AVERAGE ACROSS A BUNCH OF TRADES
            for specific_trade in trades_in_position.index[trades_in_position]:
                value = trades.loc[specific_trade, "value"]
                value *= -1 if trades.loc[specific_trade, "from"] == address else 1  # type: ignore
                sum_value += value
                sum_product_of_open_share_price_and_value += (
                    value * share_price.loc[trades.loc[specific_trade, "block_number"]]
                )

            # WEIGHTED AVERAGR FROM A MARGINAL UPDATE
            previous_balance = wallet.shorts[mint_time].balance if mint_time in wallet.shorts else 0
            previous_share_price = wallet.shorts[mint_time].open_share_price if mint_time in wallet.shorts else 0

            marginal_position_change = FixedPoint(scaled_value=balance)
            marginal_open_share_price = FixedPoint(scaled_value=int(trades.share_price))  # type: ignore

            new_balance = previous_balance + marginal_position_change

            if new_balance == 0:
                # remove key of "mint_time" from the "wallet.shorts" dict
                wallet.shorts.pop(mint_time, None)
            else:
                new_open_share_price = (
                    previous_balance * previous_share_price
                    + marginal_position_change
                    * marginal_open_share_price
                    / (previous_balance + marginal_position_change)
                )
                wallet.shorts.update(
                    {
                        mint_time: Short(
                            balance=new_balance,
                            open_share_price=new_open_share_price,
                        )
                    }
                )
        elif asset_type == "LONG":
            previous_balance = wallet.longs[mint_time].balance if mint_time in wallet.longs else 0
            new_balance = previous_balance + FixedPoint(scaled_value=balance)
            if new_balance == 0:
                # remove key of "mint_time" from the "wallet.longs" dict
                wallet.longs.pop(mint_time, None)
            wallet.longs.update({mint_time: Long(balance=new_balance)})
        elif asset_type == "LP":
            wallet.lp_tokens += FixedPoint(scaled_value=balance)
    return wallet


Info = NamedTuple(
    "Info", wallet=pd.DataFrame, positions=pd.DataFrame, deltas=pd.DataFrame, open_share_price=pd.DataFrame
)


def get_agent_info(session=None) -> dict[str, Info]:
    """Arrange agent wallet info for plotting, while calculating open share price."""
    if session is None:
        session = postgres.initialize_session()
    all_agent_wallet_info = postgres.get_wallet_info_history(session)
    agent_info = {}
    for agent, wallet in all_agent_wallet_info.items():
        share_price = wallet["sharePrice"].rename({"sharePrice": "share_price"})

        # Create positions
        positions = wallet.loc[:, wallet.columns[:-2]].copy()
        positions = positions.where(positions != 0, pd.NA)

        # Create deltas
        deltas = positions.diff()
        deltas.iloc[0] = positions.iloc[0]

        # Create NaNs of the same size as deltas
        share_price_on_increases = pd.DataFrame(data=pd.NA, index=deltas.index, columns=deltas.columns)

        # Replace positive deltas with share_price
        share_price_on_increases = share_price_on_increases.where(deltas <= 0, share_price, axis=0)

        # Fill forward to replace NaNs, to have updated share prices only on position increases
        share_price_on_increases.fillna(method="ffill", inplace=True, axis=0)

        # Calculate weighted average share price across all deltas
        # weighted_average_share_price = (share_price_on_increases * deltas).cumsum(axis=0) / positions
        weighted_average_share_price = pd.DataFrame(data=pd.NA, index=deltas.index, columns=deltas.columns)
        weighted_average_share_price.iloc[0] = share_price_on_increases.iloc[0]
        for row in deltas.index[1:]:
            # index positive deltas
            cols = deltas.loc[row, :] > 0

            new_avg = []
            if len(cols) > 0:
                # calculate update
                # new_avg = (old_amount * old_avg + delta_amount * delta_avg) / (old_amount + delta_amount)
                new_avg = (
                    share_price_on_increases.loc[row, cols] * deltas.loc[row, cols]
                    + weighted_average_share_price.loc[row - 1, cols] * positions.loc[row - 1, cols]
                ) / (deltas.loc[row, cols] + positions.loc[row - 1, cols])

            # keep previous result where delta isn't positive, otherwise replace with new_avg
            weighted_average_share_price.loc[row, :] = weighted_average_share_price.loc[row - 1, :].where(
                ~cols, new_avg, axis=0
            )

        agent_info[agent] = Info(
            wallet=wallet,
            positions=positions,
            deltas=deltas,
            open_share_price=share_price_on_increases,
        )
    return agent_info


def calculate_pnl(pool_config, pool_info, checkpoint_info):
    """Calculate pnl for all agents."""
    #  pylint: disable=too-many-locals
    session = postgres.initialize_session()
    all_agent_info = get_agent_info(session)
    position_duration = pool_config.positionDuration.iloc[0]

    for _, agent_info in all_agent_info.items():
        wallet, positions, deltas, open_share_price = agent_info
        for block in agent_info.wallet.index:
            position = positions.loc[block]
            current_wallet = wallet.loc[block, :]
            state = pool_info.loc[block]
            if block in checkpoint_info.index:  # a checkpoint exists
                current_checkpoint = checkpoint_info.loc[block]
                maturity = current_checkpoint["timestamp"] + pd.Timedelta(seconds=position_duration)
            else:
                maturity = None

            spot_price = calculate_spot_price(
                state.shareReserves,
                state.bondReserves,
                state.lpTotalSupply,
                maturity,
                current_wallet.timestamp,
                position_duration,
            )

            pnl = 0
            for position_name in positions.columns:
                if position_name.startswith("LP"):
                    # LP value (TODO: check why certain agents own more than 100% of the pool)
                    total_lp_value = state.shareReserves * state.sharePrice + state.bondReserves * spot_price
                    share_of_pool = position.LP / state.lpTotalSupply
                    assert share_of_pool < 1, "share_of_pool must be less than 1"
                    pnl += share_of_pool * total_lp_value
                elif position_name.startswith("LONG"):
                    # LONG value
                    pnl += position.loc[position_name] * spot_price
                elif position_name.startswith("SHORT"):
                    # SHORT value is calculated as the:
                    # total amount paid for the position (position * 1)
                    # minus the closing cost (position * spot_price)
                    # this equals position * (1 - spot_price)
                    pnl += position.loc[position_name] * (1 - spot_price)

            wallet.loc[block, "pnl"] = pnl
        agent_info = wallet, positions, deltas, open_share_price
    return all_agent_info


def plot_pnl(all_agent_info, axes):
    """Plots the pnl data"""
    first_agent = list(all_agent_info.keys())[0]
    first_wallet = all_agent_info[first_agent].wallet

    # pre-allocate plot_data block of maximum size, 1 row for each block, 1 column for each agent
    plot_data = pd.DataFrame(pd.NA, index=first_wallet.index, columns=all_agent_info.keys())
    for agent, agent_info in all_agent_info.items():
        wallet, _, _, _ = agent_info
        # insert agent's pnl into the plot_data block
        plot_data.loc[wallet.index, agent] = wallet["pnl"]

    # plot everything in one go
    axes.plot(plot_data)

    # change y-axis unit format to #,###.0f
    axes.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(int(x), ",")))

    # TODO fix these top use axes
    axes.set_xlabel("block timestamp")
    axes.set_ylabel("pnl")
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_title("pnl over time")

    axes.legend()

    # %%
