"""Script for fuzzing profit values on immediately opening & closing a long or short."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict

import numpy as np
from fixedpointmath import FixedPoint
from hyperlogs import ExtendedJSONEncoder

from agent0.interactive_fuzz.setup_fuzz import setup_fuzz


def main():
    """Primary entrypoint."""
    # Setup the environment
    log_filename = ".logging/fuzz_profit_check.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(log_filename)

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

    # Generate funded trading agent
    long_agent = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="alice")
    # Open a long
    open_long_event = long_agent.open_long(base=trade_amount)
    # Let some time pass, as long as it is less than a checkpoint
    chain.advance_time(
        rng.integers(low=0, high=interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration - 1),
        create_checkpoints=True,
    )
    # Close the long
    close_long_event = long_agent.close_long(
        maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
    )

    # Generate funded trading agent
    short_agent = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="bob")
    # Open a short
    # Set trade amount to the new wallet position (due to losing money from the previous open/close)
    trade_amount = short_agent.wallet.balance.amount
    open_short_event = short_agent.open_short(bonds=trade_amount)
    # Let some time pass, as long as it is less than a checkpoint
    chain.advance_time(
        rng.integers(low=0, high=interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration - 1),
        create_checkpoints=True,
    )
    # Close the short
    close_short_event = short_agent.close_short(
        maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
    )

    # Ensure that the prior trades did not result in a profit
    check_data = {
        "trade_amount": trade_amount,
        "long_agent": long_agent,
        "short_agent": short_agent,
        "long_events": {"open": open_long_event, "close": close_long_event},
        "short_events": {"open": open_short_event, "close": close_short_event},
    }
    if invariant_check_failed(
        check_data,
        random_seed,
        interactive_hyperdrive,
    ):
        raise AssertionError(f"Testing failed; see logs in {log_filename}")


def invariant_check_failed(
    check_data,
    random_seed,
    interactive_hyperdrive,
):
    """Check the pool state invariants.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    random_seed: int
        Random seed used to run the experiment.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.

    Returns
    -------
    bool
        If true, at least one of the checks failed.
    """
    failed = False
    if check_data["long_events"]["close"].base_amount >= check_data["long_events"]["open"].base_amount:
        logging.critical(
            (
                "LONG: Amount returned on closing was too large.\n"
                "base_amount_returned=%s should not be >= base_amount_proided=%s"
            ),
            check_data["long_events"]["close"].base_amount,
            check_data["long_events"]["open"].base_amount,
        )
        failed = True
    if check_data["long_agent"].wallet.balance.amount >= check_data["trade_amount"]:
        logging.critical(
            "LONG: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
            check_data["long_agent"].wallet.balance.amount,
            check_data["trade_amount"],
        )
        failed = True
    if check_data["short_events"]["close"].base_amount >= check_data["short_events"]["open"].base_amount:
        logging.critical(
            (
                "SHORT: Amount returned on closing was too large.\n"
                "base_amount_returned=%s should not be >= base_amount_proided=%s"
            ),
            check_data["short_events"]["close"].base_amount,
            check_data["short_events"]["open"].base_amount,
        )
        failed = True
    if check_data["short_agent"].wallet.balance.amount >= check_data["trade_amount"]:
        logging.critical(
            "SHORT: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
            check_data["short_agent"].wallet.balance.amount,
            check_data["trade_amount"],
        )
        failed = True

    if failed:
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

    return failed


if __name__ == "__main__":
    main()
