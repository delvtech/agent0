"""Script to export all tables from the database and write as a CSV file."""

import os

from chainsync.db.base import initialize_session
from chainsync.db.hyperdrive import (
    get_checkpoint_info,
    get_current_wallet,
    get_pool_analysis,
    get_pool_config,
    get_pool_info,
    get_ticker,
    get_transactions,
    get_wallet_deltas,
    get_wallet_pnl,
)

DATA_DIR = ".db_data_dump/"


if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# postgres session
db_session = initialize_session()

# Decimals at this point are already set to the right precision
# so to_csv keeps precision
# Loading however needs to take into account reading in as string
# then converting to Decimal with right precision

## Base tables
get_pool_config(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "pool_config.csv"))
get_checkpoint_info(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "checkpoint_info.csv"))
get_pool_info(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "pool_info.csv"))
get_wallet_deltas(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "wallet_deltas.csv"))
get_transactions(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "transactions.csv"))

## Analysis tables
get_pool_analysis(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "pool_analysis.csv"))
get_current_wallet(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "current_wallet.csv"))
get_ticker(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "ticker.csv"))
get_wallet_pnl(db_session, coerce_float=False).to_csv(os.path.join(DATA_DIR, "wallet_pnl.csv"))
