"""Get environment arguments for bots"""
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Literal

from elfpy import DEFAULT_LOG_MAXBYTES


class LogLevel(Enum):
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


# TODO: do we need this to be enviroment variables, why not add to the simulator Config?
@dataclass
class EnvironmentArguments:
    # Env passed in is a string "true"
    halt_on_errors: bool = False
    devnet: bool = True
    rpc_url: str = "http://ethereum:8545"
    log_filename: str = "testnet_bots"
    log_level: LogLevel = LogLevel.INFO
    max_bytes: int = DEFAULT_LOG_MAXBYTES
    num_louie: int = 0
    num_frida: int = 0
    num_random: int = 4
    trade_chance: float = 0.1
    # Env passed in is a string "true"
    alchemy: bool = False
    artifacts_url: str = "http://artifacts:80"


def get_env_args() -> EnvironmentArguments:
    """Define & parse arguments from stdin.
    List of arguments:
        log_filename : Optional output filename for logging. Default is "testnet_bots".
        log_level : Logging level, should be in ["DEBUG", "INFO", "WARNING"]. Default is "INFO".
        max_bytes : Maximum log file output size, in bytes. Default is 1MB.
        num_louie : Number of Long Louie agents to run. Default is 0.
        num_frida : Number of Fixed Rate Frida agents to run. Default is 0.
        num_random: Number of Random agents to run. Default is 0.
        trade_chance : Chance for a bot to execute a trade. Default is 0.1.
    Returns
    -------
    parser : dict
    """

    # make sure we get a valid log level, default to INFO
    log_level_str: str = os.environ.get("BOT_LOG_LEVEL", "INFO")
    log_level = LogLevel.__members__.get(log_level_str)
    if log_level is None:
        log_level = LogLevel.INFO

    args = EnvironmentArguments(
        # Env passed in is a string "true"
        halt_on_errors=(os.environ.get("HALT_ON_ERRORS", "false") == "true"),
        devnet=(os.environ.get("BOT_DEVNET", "true") == "true"),
        rpc_url=os.environ.get("BOT_RPC_URL", "http://ethereum:8545"),
        log_filename=os.environ.get("BOT_LOG_FILENAME", "testnet_bots"),
        log_level=log_level,
        max_bytes=int(os.environ.get("BOTS_MAX_BYTES", DEFAULT_LOG_MAXBYTES)),
        num_louie=int(os.environ.get("BOT_NUM_LOUIE", 0)),
        num_frida=int(os.environ.get("BOT_NUM_FRIDA", 0)),
        num_random=int(os.environ.get("BOT_NUM_RANDOM", 4)),
        trade_chance=float(os.environ.get("BOT_TRADE_CHANCE", 0.1)),
        # Env passed in is a string "true"
        alchemy=(os.environ.get("BOT_ALCHEMY", "false") == "true"),
        artifacts_url=os.environ.get("BOT_ARTIFACTS_URL", "http://artifacts:80"),
    )

    return args
