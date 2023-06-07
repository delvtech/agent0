"""State object for setting experiment configuration"""
from __future__ import annotations
from typing import Any
import json
import logging
from dataclasses import dataclass, field
import numpy as np
from numpy.random._generator import Generator as NumpyGenerator


import elfpy.types as types
import elfpy.utils.outputs as output_utils



@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class Config(types.FrozenClass):
    """Data object for storing user simulation config parameters"""

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    # Temporary
    do_dataframe_states: bool = False

    # Market
    # total size of the market pool (shares)
    target_liquidity: float = 1e6
    # fraction of pool liquidity
    target_volume: float = 0.01
    # years since the vault was opened
    init_vault_age: float = 0.0

    # TODO: Move this out of config, it should be computed in simulator init based on config values
    # the underlying variable (e.g. from a vault) APR at each time step; the default is overridden in __post_init__
    variable_apr: list[float] = field(default_factory=lambda: [-1])

    # TODO: Move this out of config, it should be computed in simulator init based on config values
    # initial market share price for the vault asset; default is overridden in __post_init__
    init_share_price: float = -1.0

    # AMM
    # Must be "Hyperdrive", or "YieldSpace"
    pricing_model_name: str = "Hyperdrive"
    # fee multiple applied to the price slippage (1-p), paid to LPs
    curve_fee_multiple: float = 0.05
    # fee multiple applied to the matured amount, paid to LPs
    flat_fee_multiple: float = 0.05
    # fee multiple applied to the curve and flat fees, paid to the governance contract
    governance_fee_multiple: float = 0.0
    # desired fixed apr for as a decimal
    target_fixed_apr: float = 0.1

    # Simulation
    # durations
    # Text description of the simulation
    title: str = "elfpy simulation"
    # in days; should be <= pool_duration
    num_trading_days: int = 3
    # agents execute trades each block
    num_blocks_per_day: int = 3
    # time lapse between token mint and expiry as days
    num_position_days: int = 90

    # users
    # shuffle order of action (as if random gas paid)
    shuffle_users: bool = True
    # list of strings naming user policies
    agent_policies: list = field(default_factory=list)
    # if True, use an initial LP agent to seed pool
    init_lp: bool = True

    # vault
    # whether or not to use compounding revenue for the underlying yield source
    compound_variable_apr: bool = True

    # logging
    # logging level, as defined by stdlib logging
    log_level: int = logging.INFO
    # filename for output logs
    log_filename: str = "simulation"

    # numerical
    # precision of calculations; max is 64
    precision: int = 64

    # random
    # int to be used for the random seed
    random_seed: int = 1
    # random number generator used in the simulation
    rng: NumpyGenerator = field(init=False, compare=False)

    # scratch space for any application-specific & extraneous parameters
    scratch: dict[Any, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        r"""init_share_price & rng are a function of other random variables"""
        self.rng = np.random.default_rng(self.random_seed)
        if self.variable_apr == [-1]:  # defaults to [-1] so this should happen right after init
            self.variable_apr = [0.05] * self.num_trading_days
        if self.init_share_price < 0:  # defaults to -1 so this should happen right after init
            self.init_share_price = float((1 + self.variable_apr[0]) ** self.init_vault_age)
        self.disable_new_attribs()  # disallow new attributes # pylint: disable=no-member # type: ignore

    def __getitem__(self, attrib) -> None:
        return getattr(self, attrib)

    def __setitem__(self, attrib, value) -> None:
        self.__setattr__(attrib, value)

    def __setattr__(self, attrib, value) -> None:
        #  variable_apr gets set to [-1] on init, then an appropriate value
        #  on post_init. So we need to check after it has been set, and only if
        #  it is not the first time being set.
        if not hasattr(self, attrib) or attrib != "variable_apr":
            super().__setattr__(attrib, value)
        else:  # only check variable apr if it is being reassigned
            super().__setattr__(attrib, value)
            self.check_variable_apr()  # check it after it has been assigned

    def __str__(self) -> str:
        # cls arg tells json how to handle numpy objects and nested dataclasses
        return json.dumps(self.__dict__, sort_keys=True, indent=2, cls=output_utils.CustomEncoder)

    def copy(self) -> Config:
        """Returns a new copy of self"""
        return Config(**{key: value for key, value in self.__dict__.items() if key not in ["rng"]})

    def check_variable_apr(self) -> None:
        r"""Verify that the variable_apr is the right length"""
        if not isinstance(self.variable_apr, list):
            raise TypeError(
                f"ERROR: variable_apr must be of type list, not {type(self.variable_apr)}."
                f"\nhint: it must be set after Config is initialized."
            )
        if len(self.variable_apr) != self.num_trading_days:
            raise ValueError(
                "ERROR: variable_apr must have len equal to num_trading_days = "
                + f"{self.num_trading_days},"
                + f" not {len(self.variable_apr)}"
            )
