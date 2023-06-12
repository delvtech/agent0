"""State object for setting experiment configuration"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.random._generator import Generator as NumpyGenerator

from elfpy import DEFAULT_LOG_MAXBYTES, DEFAULT_LOG_LEVEL, types
from elfpy.utils import outputs as output_utils


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class BotConfig(types.FrozenClass):
    """Parameters that can be set either locally or passed from docker."""

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    # whether to run on alchemy
    alchemy: bool = False
    # url for retrieving the contract artifacts
    artifacts_url: str = "http://localhost:80"
    # whether to run on devnet
    devnet: bool = True
    # if true, stop executing when trade errors occur
    halt_on_errors: bool = False
    # optional output filename for logging
    log_filename: str = "agent0-bots"
    # log level; should be in ["DEBUG", "INFO", "WARNING"]
    log_level: int = DEFAULT_LOG_LEVEL
    # log location; if True, save to file and write to stdout, else just save to file
    log_file_and_stdout: bool = False
    # maximum log file output size, in bytes
    max_bytes: int = DEFAULT_LOG_MAXBYTES
    # location of RPC
    rpc_url: str = "http://localhost:8545"
    # chance for a bot to execute a trade
    trade_chance: float = 0.1
    # int to be used for the random seed
    random_seed: int = 1
    # risk_threshold has different interpretations for different bots.
    # In general the bot will be more risk averse as it grows to infinity.
    # A value of 0 will usually disable it.
    risk_threshold: float = 0.0
    # random number generator used in the simulation
    rng: NumpyGenerator = field(init=False, compare=False)
    # scratch space for any application-specific & extraneous parameters
    scratch: dict[Any, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.rng = np.random.default_rng(self.random_seed)

    def __getitem__(self, attrib) -> None:
        return getattr(self, attrib)

    def __setitem__(self, attrib, value) -> None:
        self.__setattr__(attrib, value)

    def __str__(self) -> str:
        # cls arg tells json how to handle numpy objects and nested dataclasses
        return json.dumps(self.__dict__, sort_keys=True, indent=2, cls=output_utils.ExtendedJSONEncoder)

    def copy(self) -> BotConfig:
        """Returns a new copy of self"""
        return BotConfig(**{key: value for key, value in self.__dict__.items() if key not in ["rng"]})

    def load_from_json(self, json_file_location: str) -> None:
        """Load configuration settings from a JSON file and update self"""
        with open(json_file_location, mode="r", encoding="UTF-8") as file:
            json_config = json.load(file)
        self.__dict__.update(**json_config)

    def save_as_json(self, json_file_location: str) -> None:
        """Save configuration settings in JSON format"""
        with open(json_file_location, mode="w", encoding="UTF-8") as file:
            json.dump(self.__dict__, file, sort_keys=True, indent=2, cls=output_utils.ExtendedJSONEncoder)
