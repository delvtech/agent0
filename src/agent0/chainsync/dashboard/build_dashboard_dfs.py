import pandas as pd
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import get_addr_to_username
from agent0.chainsync.db.hyperdrive import get_all_traders, get_pool_info, get_position_snapshot, get_trade_events

from .build_fixed_rate import build_fixed_rate
from .build_leaderboard import build_leaderboard
from .build_ohlcv import build_ohlcv
from .build_outstanding_positions import build_outstanding_positions
from .build_ticker import build_ticker
from .build_variable_rate import build_variable_rate
from .usernames import build_user_mapping


def build_dashboard_dfs(
    hyperdrive_address: str, session: Session, max_live_blocks: int = 5000, max_ticker_rows=1000
) -> dict:

    out_dfs: dict[str, pd.DataFrame] = {}

    freq = None
    # Wallet addr to username mapping
    trader_addrs = get_all_traders(session, hyperdrive_address=hyperdrive_address)
    addr_to_username = get_addr_to_username(session)
    user_map = build_user_mapping(trader_addrs, addr_to_username)

    pool_info = get_pool_info(
        session, hyperdrive_address=hyperdrive_address, start_block=-max_live_blocks, coerce_float=False
    )

    # Get a block to timestamp mapping dataframe
    block_to_timestamp = pool_info[["block_number", "timestamp"]]

    # TODO generalize this
    # We check the block timestamp difference since we're running
    # either in real time mode or rapid 312 second per block mode
    # Determine which one, and set freq respectively
    if freq is None:
        if len(pool_info) > 2:
            time_diff = pool_info.iloc[-1]["timestamp"] - pool_info.iloc[-2]["timestamp"]
            if time_diff > pd.Timedelta("1min"):
                freq = "D"
            else:
                freq = "5min"

    # TODO these trade events won't show the token delta for withdrawal shares
    # for RemoveLiquidity
    trade_events = get_trade_events(
        session, hyperdrive_address=hyperdrive_address, all_token_deltas=False, coerce_float=False
    )
    # Adds user lookup to the ticker
    out_dfs["display_ticker"] = build_ticker(trade_events, user_map, block_to_timestamp)

    # get wallet pnl and calculate leaderboard
    # We use an exact query block since the position snapshot table
    # could be getting updated under the hood.
    query_block = int(out_dfs["display_ticker"]["Block Number"].iloc[0])
    latest_wallet_pnl = get_position_snapshot(
        session,
        hyperdrive_address=hyperdrive_address,
        start_block=query_block,
        end_block=query_block + 1,
        coerce_float=False,
    )
    out_dfs["leaderboard"] = build_leaderboard(latest_wallet_pnl, user_map)

    # build ohlcv and volume
    out_dfs["ohlcv"] = build_ohlcv(pool_info, freq=freq)
    # build rates
    out_dfs["fixed_rate"] = build_fixed_rate(pool_info)
    out_dfs["variable_rate"] = build_variable_rate(pool_info)

    # build outstanding positions plots
    out_dfs["outstanding_positions"] = build_outstanding_positions(pool_info)

    return out_dfs
