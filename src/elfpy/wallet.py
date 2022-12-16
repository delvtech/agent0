"""
Implements abstract classes that control user behavior
"""

from dataclasses import dataclass, field

from elfpy.utils.outputs import float_to_string


@dataclass(frozen=False)
class Wallet:
    """
    Stores what's in the agent's wallet

    Arguments
    ---------
    address : int
        The trader's address.
    base : float
        The base assets that held by the trader.
    lp : float
        The LP tokens held by the trader.
    longs : dict
        The long positions held by the trader.
    shorts : dict
        The short positions held by the trader.
    margin : dict
        The margin accounts controlled by the trader.
    effective_price : float
        The effective price paid on a particular trade. This is only populated
        for some transactions.
    fees_paid : float
        The fees paid by the wallet.
    """

    # pylint: disable=too-many-instance-attributes
    # dataclasses can have many attributes

    # fungible
    address: int
    base: float
    lp: float = 0  # pylint: disable=invalid-name

    # non-fungible (identified by mint_time, stored as dict)
    longs: dict = field(default_factory=dict)
    shorts: dict = field(default_factory=dict)
    margin: dict = field(default_factory=dict)

    # TODO: This isn't used for short trades.
    effective_price: float = field(init=False)  # calculated after init, only for transactions
    fees_paid: float = 0

    def __post_init__(self):
        """Post initialization function"""
        # check if this represents a trade (one side will be negative)
        total_tokens = sum(list(self.longs.values()))
        if self.base < 0 or total_tokens < 0:
            self.effective_price = total_tokens / self.base

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
