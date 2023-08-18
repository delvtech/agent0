from eth_typing import BlockNumber
from sqlalchemy.orm import Session


def data_chain_to_db(
    block_number: BlockNumber,
    session: Session,
) -> None:
    """Function to query postgres data tables and insert to analysis tables"""
    # TODO currently doing analysis on a single block, might want to batch process
    # TODO calculate fixed rate
    # TODO calculate spot prices
    # TODO calculate base buffer
    # combined_data["base_buffer"] = combined_data["longs_outstanding"] / combined_data["share_price"] + config_data["minimumShareReserves"]

    # TODO calculate current wallet positions for this block
    # This should be done from the deltas, not queries from chain

    # TODO calculate pnl through closeout pnl

    # TODO Build ticker from wallet delta

    pass
