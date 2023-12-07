"""Runs all fuzz tests forever."""

from agent0.interactive_fuzz import (
    fuzz_hyperdrive_balance,
    fuzz_long_short_maturity_values,
    fuzz_path_independence,
    fuzz_profit_check,
)


def main():
    """Runs all fuzz tests"""
    num_trades = 10
    num_paths_checked = 10
    while True:
        fuzz_hyperdrive_balance(num_trades)
        fuzz_long_short_maturity_values(num_trades)
        fuzz_path_independence(num_trades, num_paths_checked)
        fuzz_profit_check()


if __name__ == "__main__":
    main()
