"""Example script for writing a custom bot config to json"""
from elfpy.bots import BotConfig

if __name__ == "__main__":
    # load the config file, which loads defaults
    config = BotConfig()

    # Write config to json
    config.save_as_json("bots_config.default.json")
