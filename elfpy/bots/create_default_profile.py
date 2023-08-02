"""Example script for writing a custom bot config to json"""
from eth_bots.core import DEFAULT_USERNAME, EnvironmentConfig

if __name__ == "__main__":
    # load the config file, which loads defaults
    config = EnvironmentConfig()

    # Add username here if adjusting configurations in this script
    config.username = DEFAULT_USERNAME

    # Write config to json
    config.save_as_json("bots_config.default.json")
