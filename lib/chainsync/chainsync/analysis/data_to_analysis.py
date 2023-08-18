import pandas as pd
from chainsync.db.hyperdrive import get_pool_info
from sqlalchemy.orm import Session

from .calc_base_buffer import calc_base_buffer
from .calc_fixed_rate import calc_fixed_rate
from .calc_spot_price import calc_spot_price


def data_to_analysis(start_block: int, end_block: int, session: Session, pool_config: pd.Series) -> None:
    """Function to query postgres data tables and insert to analysis tables"""
    # Get data
    pool_info = get_pool_info(session, start_block, end_block, coerce_float=False)

    # Calculate spot prices
    spot_prices = calc_spot_price(
        pool_info["shareReserves"],
        pool_info["bondReserves"],
        pool_config["initialSharePrice"],
        pool_config["invTimeStretch"],
    )

    # Calculate fixed rate
    fixed_rates = calc_fixed_rate(spot_prices, pool_config["positionDuration"])

    # Calculate base buffer
    base_buffer = calc_base_buffer(
        pool_info["longsOutstanding"], pool_info["sharePrice"], pool_config["minimumShareReserves"]
    )

    # TODO calculate current wallet positions for this block
    # This should be done from the deltas, not queries from chain

    # TODO calculate pnl through closeout pnl

    # TODO Build ticker from wallet delta

    pass
