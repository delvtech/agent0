"""Testing for functions in src/elfpy/utils/post_processing.py"""

import unittest
import pandas as pd

import elfpy.utils.post_processing as post_processing


class PostProcessingTests(unittest.TestCase):
    """Unit tests for dataframe post-processing utilities"""

    def test_add_pnl_columns(self):
        """The func add a "pnl" column to the pandas dataframe"""
        trade_balance = 1
        num_trades = 3
        wallet_values_in_base = {
            f"agent_0_base": [trade_balance] * num_trades,
            f"agent_0_lp_tokens": [trade_balance] * num_trades,
            f"agent_0_total_longs": [trade_balance] * num_trades,
            f"agent_0_total_shorts": [trade_balance] * num_trades,
            f"agent_1_base": [trade_balance] * num_trades,
            f"agent_1_lp_tokens": [trade_balance] * num_trades,
            f"agent_1_total_longs": [trade_balance] * num_trades,
            f"agent_1_total_shorts": [trade_balance] * num_trades,
            f"agent_2_base": [trade_balance] * num_trades,
            f"agent_2_lp_tokens": [trade_balance] * num_trades,
            f"agent_2_total_longs": [trade_balance] * num_trades,
            f"agent_2_total_shorts": [trade_balance] * num_trades,
        }
        test_df = pd.DataFrame.from_dict(wallet_values_in_base)
        post_processing.add_pnl_columns(test_df)
        for trade_number in range(num_trades):
            for agent_id in [0, 1, 2]:
                assert test_df[f"agent_{agent_id}_pnl"].iloc[trade_number] == trade_balance * 4
