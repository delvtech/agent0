# pylint: disable=duplicate-code
"""
basic simulation
consists of only two agents: single_LP and single_short
each only does their action once, then liquidates at the end
this tests pool bootstrap behavior since it doesn't use init_LP to seed the pool
"""

import time
import os

from test_trade import BaseTradeTest

from elfpy.utils.float_to_string import float_to_string

if os.scandir("config"):
    config_file = os.path.join(os.pardir, os.getcwd(), "config", "example_config.toml")
else:
    config_file = os.path.join(os.pardir, os.getcwd(), "example_config.toml")

lp_base = BaseLPTest()

# run a test
override_dict = {
    # "num_blocks_per_day": int(24 * 60 * 60 / 12),  # 12 second block time
    # "verbose": True,
    "pricing_model_name": "Hyperdrive",
    "shuffle_users": False,
    "init_LP": False,
    "verbose": True,
}

start = time.time()
lp_base.run_base_lp_test(
    user_policies=["single_LP", "single_short"], config_file=config_file, additional_overrides=override_dict
)
dur = time.time() - start
if dur > 1:
    output_string = f"test took {float_to_string(dur*1000,precision=2)} milliseconds"
else:
    output_string = f"test took {float_to_string(dur,precision=2)} seconds"
print(output_string)
