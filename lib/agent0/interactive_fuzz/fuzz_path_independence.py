"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed."""
# %%
from __future__ import annotations

import json
import logging
from dataclasses import asdict

import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint
from hyperlogs import ExtendedJSONEncoder, setup_logging

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.state.hyperdrive_actions import HyperdriveActionType

# Pylint UPPER_CASE name conventions shouldn't always apply in notebooks.
# pylint: disable=invalid-name


# %%
# Set global defaults
NUM_TRADES = 3
NUM_PATHS_CHECKED = 10

# %%
# Setup logging
log_filename = ".logging/fuzz_path_independence.log"
setup_logging(
    log_filename=log_filename,
    delete_previous_logs=True,
    log_stdout=False,
)

# %%
# Parameters for local chain initialization, defines defaults in constructor
chain_config = LocalChain.Config()
chain = LocalChain(config=chain_config)
random_seed = np.random.randint(low=1, high=99999999)  # No seed, we want this to be random every time it is executed
rng = np.random.default_rng(random_seed)

# %%
# Parameters for pool initialization.
initial_pool_config = InteractiveHyperdrive.Config()
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)


# %%
# Generate a list of agents that execute random trades
available_actions = np.array([HyperdriveActionType.OPEN_LONG, HyperdriveActionType.OPEN_SHORT])
min_trade = interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount
trade_list: list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]] = []
for agent_index in range(NUM_TRADES):  # 1 agent per trade
    budget = FixedPoint(
        scaled_value=int(np.floor(rng.uniform(low=min_trade.scaled_value * 10, high=int(1e23))))
    )  # Give a little extra money to account for fees
    agent = interactive_hyperdrive.init_agent(base=budget, eth=FixedPoint(100))
    trade_type = rng.choice(available_actions, size=1)[0]
    trade_amount_base = FixedPoint(
        scaled_value=int(
            rng.uniform(
                low=min_trade.scaled_value,
                high=int(
                    budget.scaled_value / 2
                ),  # Don't trade all of their money, to make sure they have enough for fees
            )
        )
    )
    trade_list.append((agent, trade_type, trade_amount_base))

# %%
# Open some trades
trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]] = []
for trade in trade_list:
    agent, trade_type, trade_amount = trade
    if trade_type == HyperdriveActionType.OPEN_LONG:
        trade_event = agent.open_long(base=trade_amount)
    elif trade_type == HyperdriveActionType.OPEN_SHORT:
        trade_event = agent.open_short(bonds=trade_amount)
    else:
        raise AssertionError(f"{trade_type=} is not supported.")
    trade_events.append((agent, trade_event))
    # randomly advance time between opening trades
    chain.advance_time(
        rng.integers(low=0, high=interactive_hyperdrive.hyperdrive_interface.pool_config.position_duration)
    )

# %%
# Snapshot the chain, so we can load the snapshot & close in different orders
chain.save_snapshot()
check_data: dict | None = None

# %%
# List of columns in pool info to check between the initial pool info and the latest pool info.
check_columns = [
    "shorts_outstanding",
    "withdrawal_shares_proceeds",
    "share_price",
    "long_exposure",
    "bond_reserves",
    "lp_total_supply",
    "longs_outstanding",
]


# %%
# Close the trades randomly & verify that the final state is unchanged
for iteration in range(NUM_PATHS_CHECKED):
    print(f"{iteration=}")
    # Load the snapshot
    chain.load_snapshot()

    # Randomly grab some trades & close them one at a time
    for trade_index in rng.permuted(list(range(len(trade_events)))):
        agent, trade = trade_events[int(trade_index)]
        if isinstance(trade, OpenLong):
            agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        if isinstance(trade, OpenShort):
            agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)

    # Check the reserve amounts; they should be unchanged now that all of the trades are closed
    pool_state_df = interactive_hyperdrive.get_pool_state(coerce_float=False)

    # On first run, save final state
    if check_data is None:
        check_data = {}
        check_data["check_pool_state_df"] = pool_state_df[check_columns].iloc[-1].copy()
        pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
        effective_share_reserves = interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state)
        check_data["hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
        check_data["effective_share_reserves"] = effective_share_reserves
        check_data["vault_shares"] = pool_state.vault_shares
        # Sanity check on static pool config
        check_data["minimum_share_reserves"] = pool_state.pool_config.minimum_share_reserves

    # On subsequent run, check against the saved final state
    else:
        # Check values not provided in the database
        pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()

        failed = False
        # Base balance
        if check_data["hyperdrive_base_balance"] != pool_state.hyperdrive_base_balance:
            logging.critical(
                "check_data['hyperdrive_base_balance']=%s != pool_state.hyperdrive_base_balance=%s",
                check_data["hyperdrive_base_balance"],
                pool_state.hyperdrive_base_balance,
            )
            failed = True
        # Effective share reserves
        if check_data[
            "effective_share_reserves"
        ] != interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state):
            logging.critical(
                "check_data['effective_share_reserves']=%s != effective_share_reserves=%s",
                check_data["effective_share_reserves"],
                interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state),
            )
            failed = True
        # Vault shares (Hyperdrive balance of vault contract)
        if check_data["vault_shares"] != pool_state.vault_shares:
            logging.critical(
                "check_data['vault_shares']=%s != pool_state.vault_shares=%s",
                check_data["vault_shares"],
                pool_state.vault_shares,
            )
            failed = True
        # Minimum share reserves
        if check_data["minimum_share_reserves"] != pool_state.pool_config.minimum_share_reserves:
            logging.critical(
                "check_data['minimum_share_reserves']=%s != pool_state.pool_config.minimum_share_reserves=%s",
                check_data["minimum_share_reserves"],
                pool_state.pool_config.minimum_share_reserves,
            )
            failed = True
        # Check that the subset of columns in initial db pool state and the latest pool state are equal
        if not check_data["check_pool_state_df"].equals(pool_state_df[check_columns].iloc[-1]):
            try:
                pd.testing.assert_series_equal(
                    check_data["check_pool_state_df"], pool_state_df[check_columns].iloc[-1], check_names=False
                )
            except AssertionError as err:
                logging.critical("Database pool info is not equal\n%s", err)
            failed = True

        if failed:
            logging.info(
                (
                    "random_seed = %s\npool_config = %s\n\npool_info = %s"
                    "\n\nlatest_checkpoint = %s\n\nadditional_info = %s"
                ),
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
