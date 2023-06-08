"""Get configuration for a bot run."""
import logging
import os
from pathlib import Path

from ape.logging import logger as ape_logger
from dotenv import load_dotenv

import elfpy.utils.outputs as output_utils
from elfpy.agents.policies import LongLouie, RandomAgent, ShortSally
from elfpy.bots.bot_info import BotInfo
from elfpy.bots.get_env_args import EnvironmentArguments
from elfpy.simulators.config import Config


# FIXME: define these args!  if we are going to accept command line args or environment variable
# args, this would be a really good place to create something with attr.s so that we can do run time
# checking to make sure that nothing incorrect is passed in, so that we can avoid typo errors.
def get_config(args: EnvironmentArguments) -> Config:
    """Instantiate a config object with elf-simulation parameters.
    Parameters
    ----------
    args : dict
        The arguments from environmental variables.
    Returns
    -------
    config : simulators.Config
        The config object.
    """
    load_dotenv(dotenv_path=f"{Path.cwd() if Path.cwd().name != 'examples' else Path.cwd().parent}/.env")
    ape_logger.set_level(logging.ERROR)
    config = Config()
    config.log_level = output_utils.text_to_log_level(args.log_level)
    random_seed_file = f".logging/random_seed{'_devnet' if args.devnet else ''}.txt"
    if os.path.exists(random_seed_file):
        with open(random_seed_file, "r", encoding="utf-8") as file:
            config.random_seed = int(file.read()) + 1
    else:  # make parent directory if it doesn't exist
        os.makedirs(os.path.dirname(random_seed_file), exist_ok=True)
    logging.info("Random seed=%s", config.random_seed)
    with open(random_seed_file, "w", encoding="utf-8") as file:
        file.write(str(config.random_seed))
    config.title = "evm bots"
    for key, value in args.__dict__.items():
        if hasattr(config, key):
            config[key] = value
        else:
            config.scratch[key] = value
    config.log_filename += "_devnet" if args.devnet else ""

    # Custom parameters for this experiment
    config.scratch["project_dir"] = Path.cwd().parent if Path.cwd().name == "examples" else Path.cwd()
    config.scratch["louie"] = BotInfo(risk_threshold=0.0, policy=LongLouie, trade_chance=config.scratch["trade_chance"])
    config.scratch["frida"] = BotInfo(policy=ShortSally, trade_chance=config.scratch["trade_chance"])
    config.scratch["random"] = BotInfo(policy=RandomAgent, trade_chance=config.scratch["trade_chance"])
    config.scratch["bot_names"] = {"louie", "frida", "random"}

    config.freeze()
    return config
