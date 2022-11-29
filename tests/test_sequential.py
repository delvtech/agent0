# pylint: disable=duplicate-code
""" Manually test things in a sequence """

import time
import os

from test_lpers import BaseLPTest

from elfpy.utils.float_to_string import float_to_string

if os.scandir("config"):
    config_file = os.path.join(os.pardir, os.getcwd(), "config", "hyperdrive_config.toml")
else:
    config_file = os.path.join(os.pardir, os.getcwd(), "hyperdrive_config.toml")

lp_base = BaseLPTest()

# run a test
override_dict = {
    # "num_blocks_per_day": int(24 * 60 * 60 / 12),  # 12 second block time
    # "verbose": True,
    "shuffle_users": False,
    "init_LP": False,
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
