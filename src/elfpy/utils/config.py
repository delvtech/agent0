import numpy as np
import pickle
import os

def set_default_config():
    """Set the default config variable in memory"""
    config_raw = {
        "min_fee": 0.1,  # decimal that assigns fee_percent
        "max_fee": 0.5,  # decimal that assigns fee_percent
        "min_target_liquidity": 1e6,  # in USD
        "max_target_liquidity": 10e6,  # in USD
        "min_target_volume": 0.001,  # fraction of pool liquidity
        "max_target_volume": 0.01,  # fration of pool liquidity
        "min_pool_apy": 0.02,  # as a decimal
        "max_pool_apy": 0.9,  # as a decimal
        "min_vault_age": 0,  # fraction of a year
        "max_vault_age": 1,  # fraction of a year
        "min_vault_apy": 0.001,  # as a decimal
        "max_vault_apy": 0.9,  # as a decimal
        "base_asset_price": 2.5e3,  # aka market price
        "pool_duration": 180,  # in days
        "num_trading_days": 180,  # should be <= pool_duration
        "floor_fee": 0,  # minimum fee percentage (bps)
        "tokens": ["base", "fyt"],
        "trade_direction": "out",
        "precision": None,
        "pricing_model_name": "Element",
        "user_type": "Random",
        "random_seed": 123,
        "verbose": False,
    }
    config = config_raw.copy()
    config["rng"] = np.random.default_rng(config["random_seed"])
    return config, config_raw

def get_utils_folder():
    parent_dir = os.path.join(os.getcwd(), os.pardir)
    if os.path.exists("src"):
        utils_folder = os.path.join("src", "elfpy", "utils")
    else:
        utils_folder = os.path.join(parent_dir, "src", "elfpy", "utils")
    return utils_folder

def load(file_name='default_config.pkl', verbose=False):
    """Loads the default config file"""
    utils_folder = get_utils_folder()
    config,config_raw = set_default_config()

    # read it back and compare:
    file_location = os.path.join(utils_folder, file_name)
    with open(file_location, 'rb') as f:
        read_back_config = pickle.load(f)
    read_back_config["rng"] = np.random.default_rng(read_back_config["random_seed"])

    if verbose and file_name == 'default_config.pkl':
        compare_configs(config, read_back_config)

    print(f"loaded {file_name}")
    return read_back_config

def save(file_name='default_config.pkl', config_raw=None, verbose=False):
    """Saves the default config file"""
    utils_folder = get_utils_folder()
    if config_raw is None:
        config,config_raw = set_default_config()

    # save the config:
    file_location = os.path.join(utils_folder, file_name)
    with open(file_location, 'wb') as f:
        pickle.dump(config_raw, f)

    # read it back and compare:
    if verbose:
        read_back_config = load()
        compare_configs(config, read_back_config)
    print(f"saved {file_name}")

def compare_configs(a,b):
    success_fail_count = (0,0)
    for (k,v) in a.items():
        if k == 'rng':
            print(k, v.bit_generator._seed_seq.entropy)
            print(k, b[k].bit_generator._seed_seq.entropy)
            if v.bit_generator._seed_seq.entropy == b[k].bit_generator._seed_seq.entropy:
                print(" seeds match")
                success_fail_count = (success_fail_count[0]+1, success_fail_count[1])
            else:
                print(" seeds don't match!")
                success_fail_count = (success_fail_count[0], success_fail_count[1]+1)
        elif v == b[k]:
            print(f"success {k}")
            success_fail_count = (success_fail_count[0]+1, success_fail_count[1])
        else:
            print(f"Failure {k}!")
            success_fail_count = (success_fail_count[0], success_fail_count[1]+1)
    print(f"Matches: {success_fail_count[0]} Failures: {success_fail_count[1]}")
    return success_fail_count[1] == 0