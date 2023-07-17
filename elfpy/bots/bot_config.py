"""State object for setting bot configuration"""
from __future__ import annotations

import json
from dataclasses import dataclass

from elfpy import types
from elfpy.bots import BotInfo
from elfpy.utils import json as output_utils

DEFAULT_USERNAME = "changeme"


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class BotConfig(types.FrozenClass):
    """Parameters that can be set either locally or passed from docker."""

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    # list of details for the desired agents
    agents: list[BotInfo] | None = None

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
