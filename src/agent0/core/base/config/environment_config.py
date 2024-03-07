"""State object for setting environment configuration"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agent0.core.base.types import FrozenClass, freezable
from agent0.hyperlogs import DEFAULT_LOG_LEVEL, DEFAULT_LOG_MAXBYTES, ExtendedJSONEncoder

DEFAULT_USERNAME = "changeme"


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class EnvironmentConfig(FrozenClass):
    """Parameters that can be set either locally or passed from docker."""

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    username: str = DEFAULT_USERNAME
    """Logical username for who is running agents."""
    halt_on_errors: bool = False
    """If true, stop executing when trade errors occur."""
    halt_on_slippage: bool = False
    """If halt_on_errors is True, halt_on_slippage controls if we halt when slippage happens"""
    crash_report_to_file: bool = False
    """
    If true, will write crash report under .crash_report directory
    including the anvil crash state.
    Since crash reports are timestamped, we set this default to false
    to avoid using lots of disk space
    """
    crash_report_file_prefix: str = ""
    """The string prefix to prepend to crash reports."""
    log_filename: str = ".logging/agent0_logs.log"
    """Optional output filename for logging."""
    log_level: int = DEFAULT_LOG_LEVEL  # INFO
    """log level; should be in [logging.DEBUG, logging.INFO, logging.WARNING]."""
    delete_previous_logs: bool = False
    """Delete_previous_logs; if True, delete existing logs at the start of the run."""
    log_stdout: bool = False
    """Log log_file_and_stdout; if True, save to file and write to stdout, else just save to file."""
    log_to_rollbar: bool = False
    """If True, enables rollbar logging."""
    log_formatter: str = "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s"
    """
    log_formatter; specifies the format in which the logger saves the logs
    see https://docs.python.org/3/library/logging.html#logrecord-attributes for which attributes can be used
    """
    max_bytes: int = DEFAULT_LOG_MAXBYTES  # int(2e6) or 2MB
    """maximum log file output size, in bytes."""
    global_random_seed: int | None = None
    """int to be used for the random seed."""
    read_retry_count: int | None = None
    """
    Number of times to retry for read smart contract calls.
    Defaults to what's being used in ethpy, which is 5.
    """
    write_retry_count: int | None = None
    """
    Number of times to retry for write smart contract calls.
    Defaults to what's being used in ethpy, which is 1.
    """
    randomize_liquidation: bool = False
    """If true, will randomize liquidation trades when liquidating."""

    def __getitem__(self, attrib) -> None:
        return getattr(self, attrib)

    def __setitem__(self, attrib, value) -> None:
        self.__setattr__(attrib, value)

    def __str__(self) -> str:
        # cls arg tells json how to handle numpy objects and nested dataclasses
        return json.dumps(self.__dict__, sort_keys=True, indent=2, cls=ExtendedJSONEncoder)

    def copy(self) -> EnvironmentConfig:
        """Returns a new copy of self.

        Returns
        -------
        EnvironmentConfig
            A copy of the environment config.
        """
        return EnvironmentConfig(**{key: value for key, value in self.__dict__.items() if key not in ["rng"]})

    def load_from_json(self, json_file_location: str) -> None:
        """Load configuration settings from a JSON file and update self.

        Arguments
        ---------
        json_file_location: str
            The path to the json file to load from.
        """
        with open(json_file_location, mode="r", encoding="UTF-8") as file:
            json_config = json.load(file)
        self.__dict__.update(**json_config)

    def save_as_json(self, json_file_location: str) -> None:
        """Save configuration settings in JSON format.

        Arguments
        ---------
        json_file_location: str
            The path for the output file.
        """
        with open(json_file_location, mode="w", encoding="UTF-8") as file:
            json.dump(self.__dict__, file, sort_keys=True, indent=2, cls=ExtendedJSONEncoder)

    def freeze(self):
        """Disallows changing existing members."""

    def disable_new_attribs(self):
        """Disallows adding new members."""

    def astype(self, _):
        """Cast all member attributes to a new type."""

    @property
    def dtypes(self):
        """Return a dict listing name & type of each member variable."""
