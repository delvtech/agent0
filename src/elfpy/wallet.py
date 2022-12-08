"""
Implements abstract classes that control user behavior
"""

from dataclasses import dataclass
from dataclasses import field

from elfpy.utils.price import calc_apr_from_spot_price


@dataclass(frozen=False)
class Wallet:
    """Stores what's in the agent's wallet"""

    # pylint: disable=too-many-instance-attributes
    # dataclasses can have many attributes

    # fungible
    address: int
    base_in_wallet: float
    lp_in_wallet: float = 0  # they're fungible!
    # non-fungible (identified by mint_time, stored as dict)
    token_in_wallet: dict = field(default_factory=dict)
    base_in_protocol: dict = field(default_factory=dict)
    token_in_protocol: dict = field(default_factory=dict)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = ""
        for key, value in vars(self).items():
            if value:  #  check if object exists
                if value != 0 and value is not None:
                    output_string += f" {key}: "
                    if isinstance(value, float):
                        output_string += f"{value}"
                    elif isinstance(value, list):
                        output_string += "[" + ", ".join([x for x in value]) + "]"
                    elif isinstance(value, dict):
                        output_string += "{" + ", ".join([f"{k}: {v}" for k, v in value.items()]) + "}"
                    else:
                        output_string += f"{value}"
        return output_string
