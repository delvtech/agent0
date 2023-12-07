"""Script for fuzzing profit values on immediately opening & closing a long or short."""
# %%
# Imports
import json
import logging
from dataclasses import asdict

import numpy as np
from fixedpointmath import FixedPoint
from hyperlogs import ExtendedJSONEncoder, setup_logging

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain

# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement
# pylint: disable=invalid-name

# %%
# Set global defaults
FAILED = False

# %%
# Setup logging
log_filename = ".logging/fuzz_profit_check.log"
setup_logging(
    log_filename=log_filename,
    delete_previous_logs=True,
    log_stdout=False,
)

# %%
# Setup local chain
chain_config = LocalChain.Config()
chain = LocalChain(config=chain_config)
random_seed = np.random.randint(low=1, high=99999999)  # No seed, we want this to be random every time it is executed
rng = np.random.default_rng(random_seed)

# %%
# Parameters for pool initialization.
initial_pool_config = InteractiveHyperdrive.Config(preview_before_trade=True)
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)

# %%
# Get a random trade amount
trade_amount = FixedPoint(
    scaled_value=int(
        np.floor(
            rng.uniform(
                low=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount.scaled_value,
                high=int(1e23),
            )
        )
    )
)

# %%
# Generate funded trading agent
hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="alice")

# %%
# Open a long and close it immediately
open_long_event = hyperdrive_agent0.open_long(base=trade_amount)
# Let some time pass, as long as it is less than a checkpoint
chain.advance_time(
    rng.integers(low=0, high=interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration - 1)
)
close_long_event = hyperdrive_agent0.close_long(
    maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
)

# %%
# Ensure that the prior trades did not result in a profit
if close_long_event.base_amount >= open_long_event.base_amount:
    logging.critical(
        (
            "LONG: Amount returned on closing was too large.\n"
            "base_amount_returned=%s should not be >= base_amount_proided=%s"
        ),
        close_long_event.base_amount,
        open_long_event.base_amount,
    )
    FAILED = True
if hyperdrive_agent0.wallet.balance.amount >= trade_amount:
    logging.critical(
        "LONG: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
        hyperdrive_agent0.wallet.balance.amount,
        trade_amount,
    )
    FAILED = True

# %%
# Open a short and close it immediately
# Set trade amount to the new wallet position (due to losing money from the previous open/close)
trade_amount = hyperdrive_agent0.wallet.balance.amount
open_short_event = hyperdrive_agent0.open_short(bonds=trade_amount)
# Let some time pass, as long as it is less than a checkpoint
chain.advance_time(
    rng.integers(low=0, high=interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration - 1)
)
close_short_event = hyperdrive_agent0.close_short(
    maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
)

# %%
# Ensure that the prior trades did not result in a profit (should be a loss bc of fee)
if close_short_event.base_amount >= open_short_event.base_amount:
    logging.critical(
        (
            "SHORT: Amount returned on closing was too large.\n"
            "base_amount_returned=%s should not be >= base_amount_proided=%s"
        ),
        close_short_event.base_amount,
        open_short_event.base_amount,
    )
    FAILED = True
if hyperdrive_agent0.wallet.balance.amount >= trade_amount:
    logging.critical(
        "SHORT: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
        hyperdrive_agent0.wallet.balance.amount,
        trade_amount,
    )
    FAILED = True

if FAILED:
    pool_state = interactive_hyperdrive.hyperdrive_interface.current_pool_state
    logging.info(
        "random_seed = %s\npool_config = %s\n\npool_info = %s\n\nlatest_checkpoint = %s\n\nadditional_info = %s",
        random_seed,
        json.dumps(asdict(pool_state.pool_config), indent=2, cls=ExtendedJSONEncoder),
        json.dumps(asdict(pool_state.pool_info), indent=2, cls=ExtendedJSONEncoder),
        json.dumps(asdict(pool_state.checkpoint), indent=2, cls=ExtendedJSONEncoder),
        json.dumps(
            {
                "hyperdrive_address": interactive_hyperdrive.hyperdrive_interface.hyperdrive_contract.address,
                "base_token_address": interactive_hyperdrive.hyperdrive_interface.base_token_contract.address,
                "spot_price": interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state),
                "fixed_rate": interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate(pool_state),
                "variable_rate": pool_state.variable_rate,
                "vault_shares": pool_state.vault_shares,
            },
            indent=2,
            cls=ExtendedJSONEncoder,
        ),
    )
    raise AssertionError(f"Testing failed; see logs in {log_filename}")
