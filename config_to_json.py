"""Example script for writing a custom bot config to json"""
from elfpy.bots import BotConfig

if __name__ == "__main__":
    # load the config file
    config = BotConfig()

    # modify params as needed
    config.random_seed = 1234
    config.log_filename = "bot_demo.log"
    config.scratch["num_louie"]: int = 4
    config.scratch["num_sally"]: int = 2
    config.scratch["num_random"]: int = 4

    # Write config to json
    config.save_as_json("my_config.json")
