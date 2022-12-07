"""
Implements abstract classes that control user behavior
"""

from dataclasses import dataclass
from dataclasses import field

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
    effective_rate: float = field(init=False)  # calculated after init, only for transactions
    stretched_time_remaining: float = None

    def __post_init__(self):
        """Post initialization function"""
        # check if this represents a trade (one side will be negative)
        total_bonds = sum(list(self.token_in_protocol.values())) + sum(list(self.token_in_wallet.values()))
        total_base = sum(list(self.base_in_protocol.values())) + self.base_in_wallet
        # in trades, one side will be neegative, and neither side can be zero
        this_is_a_trade = (total_base < 0 or total_bonds < 0) and total_bonds != 0
        if this_is_a_trade and self.stretched_time_remaining != 0:
            self.effective_price = abs(total_base / total_bonds)
            self.effective_rate = calc_apr_from_spot_price(self.effective_price, self.stretched_time_remaining)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = ""
        for key, value in vars(self).items():
            if value:  #  check if object exists
                vars_not_to_display = ["stretched_time_remaining"]
                if value != 0 and value is not None and key not in vars_not_to_display:
                    output_string += f" {key}: "
                    if isinstance(value, float):
                        if key in ["effective_price", "effective_rate"]:
                            precision = 4
                        else:
                            precision = 3
                        output_string += f"{float_to_string(value, precision=precision)}"
                    elif isinstance(value, list):
                        output_string += "[" + ", ".join([float_to_string(x) for x in value]) + "]"
                    elif isinstance(value, dict):
                        output_string += "{" + ", ".join([f"{k}: {float_to_string(v)}" for k, v in value.items()]) + "}"
                    else:
                        output_string += f"{value}"
        return output_string
