# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3.10.6 64-bit
#     language: python
#     name: python3
# ---

import test_trade
import test_lpers
import time
import os
if os.scandir("config"):
    config_file = os.path.join(os.pardir, os.getcwd(), "config", "hyperdrive_config.toml")
else:
    config_file = os.path.join(os.pardir, os.getcwd(), "hyperdrive_config.toml")
from elfpy.utils.fmt import *   # float→str formatter, also imports numpy as np

# create object
# based = test_trade.BaseTradeTest()
LPbase = test_lpers.BaseLPTest()


# run a test
override_dict = {
    # "num_blocks_per_day": int(24 * 60 * 60 / 12),  # 12 second block time
    "verbose": True,
}

# # %time based.run_base_trade_test(policy="single_long", additional_overrides=override_dict)
start = time.time()
LPbase.run_base_lp_test(user_policies=["simple_LP"], config_file=config_file, additional_overrides=override_dict)
dur = time.time() - start
print(f"test took ", end=f"{fmt(dur,precision=2)} seconds" if dur>1 else f"{fmt(dur*1000,precision=2)} milliseconds")