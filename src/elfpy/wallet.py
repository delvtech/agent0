"""
Implements abstract classes that control user behavior
"""

from dataclasses import dataclass, field

from elfpy.utils.outputs import float_to_string


@dataclass(frozen=False)
class Wallet:
    """Stores what's in the agent's wallet"""

    # pylint: disable=too-many-instance-attributes
    # dataclasses can have many attributes

    # fungible
    address: int
    base_in_wallet: float
    lp_in_wallet: float = 0  # they're fungible!
    fees_paid: float = 0
    # non-fungible (identified by mint_time, stored as dict)
    token_in_wallet: dict = field(default_factory=dict)
    base_in_protocol: dict = field(default_factory=dict)
    token_in_protocol: dict = field(default_factory=dict)
    effective_price: float = field(init=False)  # calculated after init, only for transactions

    def __post_init__(self):
        """Post initialization function"""
        # check if this represents a trade (one side will be negative)
        total_tokens = sum(list(self.token_in_wallet.values()))
        if self.base_in_wallet < 0 or total_tokens < 0:
            self.effective_price = total_tokens / self.base_in_wallet

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = ""
        for key, value in vars(self).items():
            if value:  #  check if object exists
                if value != 0:
                    output_string += f" {key}: "
                    if isinstance(value, float):
                        output_string += f"{float_to_string(value)}"
                    elif isinstance(value, list):
                        output_string += "[" + ", ".join([float_to_string(x) for x in value]) + "]"
                    elif isinstance(value, dict):
                        output_string += "{" + ", ".join([f"{k}: {float_to_string(v)}" for k, v in value.items()]) + "}"
                    else:
                        output_string += f"{value}"
        return output_string
