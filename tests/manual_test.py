# pylint: disable=duplicate-code
""" Manually test things """

import time
import os

from test_lpers import BaseLPTest

from elfpy.utils.float_to_string import float_to_string

if os.scandir("config"):
    config_file = os.path.join(os.pardir, os.getcwd(), "config", "example_config.toml")
else:
    config_file = os.path.join(os.pardir, os.getcwd(), "example_config.toml")

LPbase = BaseLPTest()

# run a test
override_dict = {
    "pricing_model_name": "Hyperdrive",
    "verbose": True,
}

start = time.time()
LPbase.run_base_lp_test(user_policies=["single_LP"], config_file=config_file, additional_overrides=override_dict)
dur = time.time() - start
print(
    f"test took ",
    end=f"{float_to_string(dur,precision=2)} seconds"
    if dur > 1
    else f"{float_to_string(dur*1000,precision=2)} milliseconds",
)
