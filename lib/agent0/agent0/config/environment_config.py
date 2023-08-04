"""State object for setting environment configuration"""
from __future__ import annotations

import json
from dataclasses import dataclass

from elfpy import DEFAULT_LOG_LEVEL, DEFAULT_LOG_MAXBYTES, types
from elfpy.utils import json as output_utils

from . import DEFAULT_USERNAME


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class EnvironmentConfig(types.FrozenClass):
    """Parameters that can be set either locally or passed from docker."""

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    # Logical username for who is running bots
    username: str = DEFAULT_USERNAME
    # Logical username for who is running bots
    username_register_url: str = "http://localhost:5002"
    # url for retrieving the contract artifacts
    artifacts_url: str = "http://localhost:80"
    # location of RPC
    rpc_url: str = "http://localhost:8545"
    # if true, stop executing when trade errors occur
    halt_on_errors: bool = False
    # optional output filename for logging
    log_filename: str = "agent0-bots"
    # log level; should be in [logging.DEBUG, logging.INFO, logging.WARNING]
    log_level: int = DEFAULT_LOG_LEVEL  # INFO
    # delete_previous_logs; if True, delete existing logs at the start of the run
    delete_previous_logs: bool = False
    # log log_file_and_stdout; if True, save to file and write to stdout, else just save to file
    log_stdout: bool = False
    # log_formatter; specifies the format in which the logger saves the logs
    # see https://docs.python.org/3/library/logging.html#logrecord-attributes for which attributes can be used
    log_formatter: str = "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s"
    # maximum log file output size, in bytes
    max_bytes: int = DEFAULT_LOG_MAXBYTES  # int(2e6) or 2MB
    # int to be used for the random seed
    random_seed: int = 1
    # abi filenames
    hyperdrive_abi: str = "IHyperdrive"
    base_abi: str = "ERC20Mintable"
    # ABI location
    abi_folder: str = "packages/hyperdrive/src/abis/"

    def __getitem__(self, attrib) -> None:
        return getattr(self, attrib)

    def __setitem__(self, attrib, value) -> None:
        self.__setattr__(attrib, value)

    def __str__(self) -> str:
        # cls arg tells json how to handle numpy objects and nested dataclasses
        return json.dumps(self.__dict__, sort_keys=True, indent=2, cls=output_utils.ExtendedJSONEncoder)

    def copy(self) -> EnvironmentConfig:
        """Returns a new copy of self"""
        return EnvironmentConfig(**{key: value for key, value in self.__dict__.items() if key not in ["rng"]})

    def load_from_json(self, json_file_location: str) -> None:
        """Load configuration settings from a JSON file and update self"""
        with open(json_file_location, mode="r", encoding="UTF-8") as file:
            json_config = json.load(file)
        self.__dict__.update(**json_config)

    def save_as_json(self, json_file_location: str) -> None:
        """Save configuration settings in JSON format"""
        with open(json_file_location, mode="w", encoding="UTF-8") as file:
            json.dump(self.__dict__, file, sort_keys=True, indent=2, cls=output_utils.ExtendedJSONEncoder)
