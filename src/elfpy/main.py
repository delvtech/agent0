"""Simulator class wraps the pricing models and markets for experiment tracking and execution"""
from __future__ import annotations
from dataclasses import dataclass, field  # types will be strings by default in 3.11
from enum import Enum

import logging
from functools import wraps
from importlib import import_module
from typing import TYPE_CHECKING, Type, Any, Dict, Optional

import numpy as np
from numpy.random import Generator

import elfpy.utils.time as time_utils
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel

if TYPE_CHECKING:
    from elfpy.agent import Agent
    from elfpy.pricing_models.base import PricingModel

# Setup barebones logging without a handler for users to adapt to their needs.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# This is the minimum allowed value to be passed into calculations to avoid
# problems with sign flips that occur when the floating point range is exceeded.
WEI = 1e-18  # smallest denomination of ether

# The maximum allowed difference between the base reserves and bond reserves.
# This value was calculated using trial and error and is close to the maximum
# difference between the reserves that will not result in a sign flip when a
# small trade is put on.
MAX_RESERVES_DIFFERENCE = 2e10

# The maximum allowed precision error.
# This value was selected based on one test not passing without it.
# apply_delta() below checks if reserves are negative within the threshold,
# and sets them to 0 if so.
# TODO: we shouldn't have to adjsut this -- we need to reesolve rounding errors
PRECISION_THRESHOLD = 1e-8


def freezable(frozen: bool = False, no_new_attribs: bool = False) -> Type:
    r"""A wrapper that allows classes to be frozen, such that existing member attributes cannot be changed"""

    def decorator(cls: Type) -> Type:
        @wraps(wrapped=cls, updated=())
        class FrozenClass(cls):
            """Subclass cls to enable freezing of attributes

            .. todo:: resolve why pyright cannot access member "freeze" when instantiated_class.freeze() is called
            """

            def __init__(self, *args, frozen=frozen, no_new_attribs=no_new_attribs, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                super().__setattr__("frozen", frozen)
                super().__setattr__("no_new_attribs", no_new_attribs)

            def __setattr__(self, attrib: str, value: Any) -> None:
                if hasattr(self, attrib) and hasattr(self, "frozen") and getattr(self, "frozen"):
                    raise AttributeError(f"{self.__class__.__name__} is frozen, cannot change attribute '{attrib}'.")
                if not hasattr(self, attrib) and hasattr(self, "no_new_attribs") and getattr(self, "no_new_attribs"):
                    raise AttributeError(
                        f"{self.__class__.__name__} has no_new_attribs set, cannot add attribute '{attrib}'."
                    )
                super().__setattr__(attrib, value)

            def freeze(self) -> None:
                """disallows changing existing members"""
                super().__setattr__("frozen", True)

            def disable_new_attribs(self) -> None:
                """disallows adding new members"""
                super().__setattr__("no_new_attribs", True)

        return FrozenClass

    return decorator


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class Config:
    """Data object for storing user simulation config parameters

    .. todo:: Rename the {trade/redemption}_fee_percent variables so that they doesn't use "percent"
    """

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    # Market
    target_liquidity: float = field(
        default=1e6, metadata={"description": "total size of the market pool (bonds + shares"}
    )
    target_volume: float = field(default=0.01, metadata={"description": "fraction of pool liquidity"})
    init_vault_age: float = field(default=0, metadata={"description": "fraction of a year since the vault was opened"})
    base_asset_price: float = field(default=2e3, metadata={"description": "market price"})
    variable_rate: list[float] = field(
        init=False, metadata={"description": "the underlying (variable) variable APR at each time step"}
    )
    init_share_price: float = field(
        init=False, metadata={"description": "initial market share price for the vault asset"}
    )

    # AMM
    pricing_model_name: str = field(
        default="Hyperdrive", metadata={"description": 'Must be "Hyperdrive", or "YieldSpace"'}
    )
    trade_fee_percent: float = field(
        default=0.05, metadata={"description": "LP fee factor (decimal) to charge for trades"}
    )
    redemption_fee_percent: float = field(
        default=0.05, metadata={"description": "LP fee factor (decimal) to charge for redemption"}
    )
    target_fixed_rate: float = field(default=0.1, metadata={"description": "desired fixed apr for as a decimal"})
    floor_fee: float = field(default=0, metadata={"description": "minimum fee percentage (bps)"})

    # Simulation
    # durations
    title: str = field(default="elfpy simulation", metadata={"description": "Text description of the simulation"})
    num_trading_days: int = field(default=3, metadata={"description": "in days; should be <= pool_duration"})
    num_blocks_per_day: int = field(default=3, metadata={"description": "int; agents execute trades each block"})
    num_position_days: int = field(
        default=90, metadata={"description": "time lapse between token mint and expiry as days"}
    )

    # users
    shuffle_users: bool = field(
        default=True, metadata={"description": "Shuffle order of action (as if random gas paid)"}
    )
    agent_policies: list = field(default_factory=list, metadata={"description": "List of strings naming user policies"})
    init_lp: bool = field(default=True, metadata={"description": "If True, use an initial LP agent to seed pool"})

    # vault
    compound_vault_rate: bool = field(
        default=True,
        metadata={"description": "Whether or not to use compounding revenue for the underlying yield source"},
    )
    init_vault_age: float = field(default=0, metadata={"description": "initial vault age"})

    # logging
    log_level: int = field(
        default=logging.INFO, metadata={"description": "Logging level, as defined by stdlib logging"}
    )
    log_filename: str = field(default="simulation.log", metadata={"description": "filename for output logs"})

    # numerical
    precision: int = field(default=64, metadata={"description": "precision of calculations; max is 64"})

    # random
    random_seed: int = field(default=1, metadata={"description": "int to be used for the random seed"})
    rng: Generator = field(
        init=False, compare=False, metadata={"description": "random number generator used in the simulation"}
    )

    def __post_init__(self) -> None:
        r"""init_share_price & rng are a function of other random variables"""
        self.rng = np.random.default_rng(self.random_seed)
        self.variable_apr = [0.05] * self.num_trading_days
        self.init_share_price = (1 + self.variable_apr[0]) ** self.init_vault_age
        self.disable_new_attribs()  # disallow new attributes # pylint: disable=no-member # type: ignore

    def __getitem__(self, key) -> None:
        return getattr(self, key)

    def __setattr__(self, attrib, value) -> None:
        if attrib == "variable_apr":
            if hasattr(self, "variable_apr"):
                self.check_variable_rate()
            super().__setattr__("variable_apr", value)
        elif attrib == "init_share_price":
            super().__setattr__("init_share_price", value)
        else:
            super().__setattr__(attrib, value)

    def check_variable_rate(self) -> None:
        r"""Verify that the variable_rate is the right length"""
        if not isinstance(self.variable_rate, list):
            raise TypeError(
                f"ERROR: variable_rate must be of type list, not {type(self.variable_rate)}."
                f"\nhint: it must be set after Config is initialized."
            )
        if not hasattr(self, "num_trading_days") and len(self.variable_rate) != self.num_trading_days:
            raise ValueError(
                "ERROR: variable_rate must have len equal to num_trading_days = "
                + f"{self.num_trading_days},"
                + f" not {len(self.variable_rate)}"
            )


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeBreakdown:
    r"""A granular breakdown of a trade.

    This includes information relating to fees and slippage.
    """

    without_fee_or_slippage: float
    with_fee: float
    without_fee: float
    fee: float


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeResult:
    r"""The result of performing a trade.

    This includes granular information about the trade details,
    including the amount of fees collected and the total delta.
    Additionally, breakdowns for the updates that should be applied
    to the user and the market are computed.
    """

    user_result: Wallet
    market_result: Wallet
    breakdown: TradeBreakdown


@dataclass
class Quantity:
    r"""An amount with a unit"""

    amount: float
    unit: TokenType


class TokenType(Enum):
    r"""A type of token"""

    BASE = "base"
    PT = "pt"


class MarketActionType(Enum):
    r"""
    The descriptor of an action in a market

    .. todo:: Add INITIALIZE_MARKET = "initialize_market"
    """

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"

    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class StretchedTime:
    r"""Stores time in units of days, as well as normalized & stretched variants

    .. todo:: Improve this constructor so that StretchedTime can be constructed from years.
    """
    days: float
    time_stretch: float
    normalizing_constant: float

    @property
    def stretched_time(self):
        r"""Returns days / normalizing_constant / time_stretch"""
        return time_utils.days_to_time_remaining(
            self.days, self.time_stretch, normalizing_constant=self.normalizing_constant
        )

    @property
    def normalized_time(self):
        r"""Format time as normalized days"""
        return time_utils.norm_days(
            self.days,
            self.normalizing_constant,
        )


@dataclass
class Position:
    r"""A Long or Short position

    Parameters
    ----------
    balance : float
        The amount of bonds that the position is short.
    open_share_price: float
        The share price at the time the short was opened.
    """

    balance: float = 0
    open_share_price: float = 0


@dataclass(frozen=False)
class Wallet:
    r"""Stores what is in the agent's wallet

    Parameters
    ----------
    address : int
        The trader's address.
    base : float
        The base assets that held by the trader.
    lp_tokens : float
        The LP tokens held by the trader.
    longs : Dict[float, Position]
        The long positions held by the trader.
    shorts : Dict[float, Position]
        The short positions held by the trader.
    fees_paid : float
        The fees paid by the wallet.
    """

    # pylint: disable=too-many-instance-attributes
    # dataclasses can have many attributes

    # agent identifier
    address: int

    # fungible
    base: float = 0
    bonds: float = 0
    lp_tokens: float = 0

    # non-fungible (identified by key=mint_time, stored as dict)
    longs: Dict[float, Position] = field(default_factory=Dict)
    shorts: Dict[float, Position] = field(default_factory=Dict)

    share_price: float = 0

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get_state(self, market_state_: MarketState) -> dict:
        r"""The wallet's current state of public variables
        .. todo:: TODO: return a dataclass instead of dict to avoid having to check keys & the get_state_keys func
        """
        lp_token_value = 0
        if self.lp_tokens > 0 and market_state_.lp_reserves > 0:  # check if LP, and avoid divide by zero
            share_of_pool = self.lp_tokens / market_state_.lp_reserves
            pool_value = (
                market_state_.bond_reserves * market.spot_price  # in base
                + market_state_.share_reserves * market_state_.share_price  # in base
            )
            lp_token_value = pool_value * share_of_pool  # in base
        share_reserves = market_state_.share_reserves
        # compute long values in units of base
        longs_value = 0
        longs_value_no_mock = 0
        for mint_time, long in self.longs.items():
            base = (
                market.close_long(self.address, long.balance, mint_time)[1].base
                if long.balance > 0 and share_reserves
                else 0.0
            )
            longs_value += base
            base_no_mock = long.balance * market.spot_price
            longs_value_no_mock += base_no_mock
        # compute short values in units of base
        shorts_value = 0
        shorts_value_no_mock = 0
        for mint_time, short in self.shorts.items():
            base = (
                market.close_short(self.address, short.open_share_price, short.balance, mint_time)[1].base
                if short.balance > 0 and share_reserves
                else 0.0
            )
            shorts_value += base
            base_no_mock = short.balance * (1 - market.spot_price)
            shorts_value_no_mock += base_no_mock
        return {
            f"agent_{self.address}_base": self.base,
            f"agent_{self.address}_lp_tokens": lp_token_value,
            f"agent_{self.address}_num_longs": len(self.longs),
            f"agent_{self.address}_num_shorts": len(self.shorts),
            f"agent_{self.address}_total_longs": longs_value,
            f"agent_{self.address}_total_shorts": shorts_value,
            f"agent_{self.address}_total_longs_no_mock": longs_value_no_mock,
            f"agent_{self.address}_total_shorts_no_mock": shorts_value_no_mock,
        }

    def get_state_keys(self) -> list:
        """Get state keys for a wallet."""
        return [
            f"agent_{self.address}_base",
            f"agent_{self.address}_lp_tokens",
            f"agent_{self.address}_num_longs",
            f"agent_{self.address}_num_shorts",
            f"agent_{self.address}_total_longs",
            f"agent_{self.address}_total_shorts",
            f"agent_{self.address}_total_longs_no_mock",
            f"agent_{self.address}_total_shorts_no_mock",
        ]


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction:
    r"""Market action specification"""
    action_type: MarketActionType = field(metadata={"description": "type of action to execute"})
    trade_amount: float = field(metadata={"description": "amount to supply for the action"})
    min_amount_out: float = field(default=0, metadata={"properties": "slippage on output, always sets a minimum"})
    wallet: Wallet = field(default_factory=Wallet, metadata={"description": "the wallet to execute the action on"})
    mint_time: Optional[float] = field(default=None, metadata={"description": "the mint time of the position to close"})


@freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketState:
    r"""The state of an AMM

    Implements a class for all that that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.  The variable_rate will most
    likely be accessible through the AMM as well.

    Attributes
    ----------
    share_reserves: float
        Quantity of shares stored in the market
    bond_reserves: float
        Quantity of bonds stored in the market
    base_buffer: float
        Base amount set aside to account for open longs
    bond_buffer: float
        Bond amount set aside to account for open shorts
    lp_reserves: float
        Amount of lp tokens
    variable_rate: float
        .. todo: fill this in
    share_price: float
        .. todo: fill this in
    init_share_price: float
        .. todo: fill this in
    trade_fee_percent : float
        The percentage of the difference between the amount paid without
        slippage and the amount received that will be added to the input
        as a fee.
    redemption_fee_percent : float
        A flat fee applied to the output.  Not used in this equation for Yieldspace.
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    time: float = 0.0
    pricing_model: PricingModel = field(default_factory=HyperdrivePricingModel)
    position_duration: StretchedTime = field(
        default_factory=lambda: StretchedTime(days=365, time_stretch=22, normalizing_constant=365)
    )
    share_reserves: float = 0.0
    bond_reserves: float = 0.0
    base_buffer: float = 0.0
    bond_buffer: float = 0.0
    lp_reserves: float = 0.0
    variable_rate: float = 0.0
    share_price: float = 1.0
    init_share_price: float = 1.0
    trade_fee_percent: float = 0.0
    redemption_fee_percent: float = 0.0


def apply_delta(simulation_state_, delta: Wallet) -> None:
    r"""Applies a delta to the market state."""
    simulation_state_.share_reserves += delta.base / simulation_state_.share_price
    simulation_state_.bond_reserves += delta
    simulation_state_.base_buffer += delta.base_buffer
    simulation_state_.bond_buffer += delta.bond_buffer
    simulation_state_.lp_reserves += delta.lp_reserves
    simulation_state_.share_price += delta.share_price

    # TODO: issue #146
    # this is an imperfect solution to rounding errors, but it works for now
    # ideally we'd find a more thorough solution than just catching errors
    # when they are.
    for key, value in simulation_state_.__dict__.items():
        if 0 > value > -PRECISION_THRESHOLD:
            logging.debug(
                ("%s=%s is negative within PRECISION_THRESHOLD=%f, setting it to 0"),
                key,
                value,
                PRECISION_THRESHOLD,
            )
            setattr(simulation_state_, key, 0)
        else:
            assert (
                value > -PRECISION_THRESHOLD
            ), f"MarketState values must be > {-PRECISION_THRESHOLD}. Error on {key} = {value}"


def trade_and_update(simulation_state_, action_details: tuple[int, MarketAction]) -> tuple[int, Wallet, Wallet]:
    r"""Execute a trade in the simulated market

    check which of 6 action types are being executed, and handles each case:

    open_long
    .. todo:: fill this in

    close_long
    .. todo:: fill this in

    open_short
    .. todo:: fill this in

    close_short
    .. todo:: fill this in

    add_liquidity
        pricing model computes new market deltas
        market updates its "liquidity pool" wallet, which stores each trade's mint time and user address
        LP tokens are also stored in user wallet as fungible amounts, for ease of use

    remove_liquidity
        market figures out how much the user has contributed (calcualtes their fee weighting)
        market resolves fees, adds this to the agent_action (optional function, to check AMM logic)
        pricing model computes new market deltas
        market updates its "liquidity pool" wallet, which stores each trade's mint time and user address
        LP tokens are also stored in user wallet as fungible amounts, for ease of use
    """
    agent_id, agent_action = action_details
    # TODO: add use of the Quantity type to enforce units while making it clear what units are being used
    # issue 216
    # for each position, specify how to forumulate trade and then execute
    if agent_action.action_type == MarketActionType.OPEN_LONG:  # buy to open long
        market_deltas, agent_deltas = simulation_state_.open_long(
            wallet_address=agent_action.wallet.address,
            trade_amount=agent_action.trade_amount,  # in base: that's the thing in your wallet you want to sell
        )
    elif agent_action.action_type == MarketActionType.CLOSE_LONG:  # sell to close long
        # TODO: python 3.10 includes TypeGuard which properly avoids issues when using Optional type
        mint_time = float(agent_action.mint_time or 0)
        market_deltas, agent_deltas = simulation_state_.close_long(
            wallet_address=agent_action.wallet.address,
            trade_amount=agent_action.trade_amount,  # in bonds: that's the thing in your wallet you want to sell
            mint_time=mint_time,
        )
    elif agent_action.action_type == MarketActionType.OPEN_SHORT:  # sell PT to open short
        market_deltas, agent_deltas = simulation_state_.open_short(
            wallet_address=agent_action.wallet.address,
            trade_amount=agent_action.trade_amount,  # in bonds: that's the thing you want to short
        )
    elif agent_action.action_type == MarketActionType.CLOSE_SHORT:  # buy PT to close short
        # TODO: python 3.10 includes TypeGuard which properly avoids issues when using Optional type
        mint_time = float(agent_action.mint_time or 0)
        open_share_price = agent_action.wallet.shorts[mint_time].open_share_price
        market_deltas, agent_deltas = simulation_state_.close_short(
            wallet_address=agent_action.wallet.address,
            trade_amount=agent_action.trade_amount,  # in bonds: that's the thing you owe, and need to buy back
            mint_time=mint_time,
            open_share_price=open_share_price,
        )
    elif agent_action.action_type == MarketActionType.ADD_LIQUIDITY:
        market_deltas, agent_deltas = simulation_state_.add_liquidity(
            wallet_address=agent_action.wallet.address,
            trade_amount=agent_action.trade_amount,
        )
    elif agent_action.action_type == MarketActionType.REMOVE_LIQUIDITY:
        market_deltas, agent_deltas = simulation_state_.remove_liquidity(
            wallet_address=agent_action.wallet.address,
            trade_amount=agent_action.trade_amount,
        )
    else:
        raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
    logging.debug(
        "%s\n%s\nagent_deltas = %s\npre_trade_market = %s",
        agent_action,
        market_deltas,
        agent_deltas,
        simulation_state_.market_state,
    )
    return (agent_id, agent_deltas, market_deltas)


def update_market(simulation_state_, market_deltas: Wallet) -> None:
    """
    Increments member variables to reflect current market conditions

    .. todo:: This order is weird. We should move everything in apply_update to update_market,
        and then make a new function called check_update that runs these checks
    """
    simulation_state_.check_market_updates(market_deltas)
    simulation_state_.market_state.apply_delta(market_deltas)


def check_market_updates(simulation_state_, market_deltas: Wallet) -> None:
    """Check market update values to make sure they are valid"""
    for key, value in market_deltas.__dict__.items():
        if value:  # check that it's instantiated and non-empty
            assert np.isfinite(value), f"markets.update_market: ERROR: market delta key {key} is not finite."


@property
def apr(simulation_state_) -> float:
    """Returns the current market apr (returns nan if shares are zero)"""
    return (
        np.nan
        if simulation_state_.market_state.share_reserves <= 0
        else price_utils.calc_apr_from_spot_price(
            price=simulation_state_.spot_price, time_remaining=simulation_state_.position_duration
        )
    )


@property
def spot_price(simulation_state_) -> float:
    """Returns the current market price of the share reserves (returns nan if shares are zero)"""
    return (
        np.nan
        if simulation_state_.market_state.share_reserves == 0
        else simulation_state_.pricing_model.calc_spot_price_from_reserves(
            market_state=simulation_state_.market_state, time_remaining=simulation_state_.position_duration
        )
    )


def get_market_state_string(simulation_state_) -> str:
    """Returns a formatted string containing all of the Market class member variables"""
    strings = [f"{attribute} = {value}" for attribute, value in simulation_state_.__dict__.items()]
    return "\n".join(strings)


def open_short(
    simulation_state_,
    wallet_address: int,
    trade_amount: float,
) -> tuple[Wallet, Wallet]:
    """
    shorts need their margin account to cover the worst case scenario (p=1)
    margin comes from 2 sources:
    - the proceeds from your short sale (p)
    - the max value you cover with base deposted from your wallet (1-p)
    these two components are both priced in base, yet happily add up to 1.0 units of bonds
    so we have the following identity:
    total margin (base, from proceeds + deposited) = face value of bonds shorted (# of bonds)

    this guarantees that bonds in the system are always fully backed by an equal amount of base
    """
    # Perform the trade.
    trade_quantity = Quantity(amount=trade_amount, unit=TokenType.PT)
    simulation_state_.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=simulation_state_.market_state,
        time_remaining=simulation_state_.position_duration,
    )
    trade_result = simulation_state_.pricing_model.calc_out_given_in(
        in_=trade_quantity,
        market_state=simulation_state_.market_state,
        time_remaining=simulation_state_.position_duration,
    )
    simulation_state_.pricing_model.check_output_assertions(trade_result=trade_result)
    # Return the market and wallet deltas.
    market_deltas = Wallet(
        d_base_asset=trade_result.market_result.d_base,
        d_token_asset=trade_result.market_result.d_bonds,
        d_bond_buffer=trade_amount,
    )
    # amount to cover the worst case scenario where p=1. this amount is 1-p. see logic above.
    max_loss = trade_amount - trade_result.user_result.d_base
    agent_deltas = Wallet(
        address=wallet_address,
        base=-max_loss,
        shorts={
            simulation_state_.time: Short(
                balance=trade_amount, open_share_price=simulation_state_.market_state.share_price
            )
        },
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def close_short(
    simulation_state_,
    wallet_address: int,
    open_share_price: float,
    trade_amount: float,
    mint_time: float,
) -> tuple[Wallet, Wallet]:
    """
    when closing a short, the number of bonds being closed out, at face value, give us the total margin returned
    the worst case scenario of the short is reduced by that amount, so they no longer need margin for it
    at the same time, margin in their account is drained to pay for the bonds being bought back
    so the amount returned to their wallet is trade_amount minus the cost of buying back the bonds
    that is, d_base = trade_amount (# of bonds) + trade_result.user_result.d_base (a negative amount, in base))
    for more on short accounting, see the open short method
    """

    # Clamp the trade amount to the bond reserves.
    if trade_amount > simulation_state_.market_state.bond_reserves:
        logging.warning(
            (
                "markets._close_short: WARNING: trade amount = %g"
                "is greater than bond reserves = %g. "
                "Adjusting to allowable amount."
            ),
            trade_amount,
            simulation_state_.market_state.bond_reserves,
        )
        trade_amount = simulation_state_.market_state.bond_reserves

    # Compute the time remaining given the mint time.
    years_remaining = time_utils.get_years_remaining(
        market_time=simulation_state_.time,
        mint_time=mint_time,
        position_duration_years=simulation_state_.position_duration.days / 365,
    )  # all args in units of years
    time_remaining = StretchedTime(
        days=years_remaining * 365,  # converting years to days
        time_stretch=simulation_state_.position_duration.time_stretch,
        normalizing_constant=simulation_state_.position_duration.normalizing_constant,
    )

    # Perform the trade.
    trade_quantity = Quantity(amount=trade_amount, unit=TokenType.PT)
    simulation_state_.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=simulation_state_.market_state,
        time_remaining=time_remaining,
    )
    trade_result = simulation_state_.pricing_model.calc_in_given_out(
        out=trade_quantity,
        market_state=simulation_state_.market_state,
        time_remaining=time_remaining,
    )
    simulation_state_.pricing_model.check_output_assertions(trade_result=trade_result)
    # Return the market and wallet deltas.
    market_deltas = Wallet(
        d_base_asset=trade_result.market_result.d_base,
        d_token_asset=trade_result.market_result.d_bonds,
        d_bond_buffer=-trade_amount,
    )
    agent_deltas = Wallet(
        address=wallet_address,
        base=(simulation_state_.market_state.share_price / open_share_price) * trade_amount
        + trade_result.user_result.d_base,  # see CLOSING SHORT LOGIC above
        shorts={
            mint_time: Short(
                balance=-trade_amount,
                open_share_price=0,
            )
        },
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def open_long(
    simulation_state_,
    wallet_address: int,
    trade_amount: float,  # in base
) -> tuple[Wallet, Wallet]:
    """
    take trade spec & turn it into trade details
    compute wallet update spec with specific details
    will be conditional on the pricing model
    """
    # TODO: Why are we clamping elsewhere but we don't apply the trade at all here?
    # issue #146
    if trade_amount <= simulation_state_.market_state.bond_reserves:
        # Perform the trade.
        trade_quantity = Quantity(amount=trade_amount, unit=TokenType.BASE)
        simulation_state_.pricing_model.check_input_assertions(
            quantity=trade_quantity,
            market_state=simulation_state_.market_state,
            time_remaining=simulation_state_.position_duration,
        )
        trade_result = simulation_state_.pricing_model.calc_out_given_in(
            in_=trade_quantity,
            market_state=simulation_state_.market_state,
            time_remaining=simulation_state_.position_duration,
        )
        simulation_state_.pricing_model.check_output_assertions(trade_result=trade_result)
        # Get the market and wallet deltas to return.
        market_deltas = Wallet(
            d_base_asset=trade_result.market_result.d_base,
            d_token_asset=trade_result.market_result.d_bonds,
            d_base_buffer=trade_result.user_result.d_bonds,
        )
        agent_deltas = Wallet(
            address=wallet_address,
            base=trade_result.user_result.d_base,
            longs={simulation_state_.time: Long(trade_result.user_result.d_bonds)},
            fees_paid=trade_result.breakdown.fee,
        )
    else:
        market_deltas = Wallet()
        agent_deltas = Wallet(address=wallet_address, base=0)
    return market_deltas, agent_deltas


def close_long(
    simulation_state_,
    wallet_address: int,
    trade_amount: float,  # in bonds
    mint_time: float,
) -> tuple[Wallet, Wallet]:
    """
    take trade spec & turn it into trade details
    compute wallet update spec with specific details
    will be conditional on the pricing model
    """

    # Compute the time remaining given the mint time.
    years_remaining = time_utils.get_years_remaining(
        market_time=simulation_state_.time,
        mint_time=mint_time,
        position_duration_years=simulation_state_.position_duration.days / 365,
    )  # all args in units of years
    time_remaining = StretchedTime(
        days=years_remaining * 365,  # converting years to days
        time_stretch=simulation_state_.position_duration.time_stretch,
        normalizing_constant=simulation_state_.position_duration.normalizing_constant,
    )

    # Perform the trade.
    trade_quantity = Quantity(amount=trade_amount, unit=TokenType.PT)
    simulation_state_.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=simulation_state_.market_state,
        time_remaining=time_remaining,
    )
    trade_result = simulation_state_.pricing_model.calc_out_given_in(
        in_=trade_quantity,
        market_state=simulation_state_.market_state,
        time_remaining=time_remaining,
    )
    simulation_state_.pricing_model.check_output_assertions(trade_result=trade_result)
    # Return the market and wallet deltas.
    market_deltas = Wallet(
        d_base_asset=trade_result.market_result.d_base,
        d_token_asset=trade_result.market_result.d_bonds,
        d_base_buffer=-trade_amount,
    )
    agent_deltas = Wallet(
        address=wallet_address,
        base=trade_result.user_result.d_base,
        longs={mint_time: Long(trade_result.user_result.d_bonds)},
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def initialize_market(
    simulation_state_,
    wallet_address: int,
    contribution: float,
    target_apr: float,
) -> tuple[Wallet, Wallet]:
    """Allows an LP to initialize the market"""
    share_reserves = contribution / simulation_state_.market_state.share_price
    bond_reserves = simulation_state_.pricing_model.calc_bond_reserves(
        target_apr=target_apr,
        time_remaining=simulation_state_.position_duration,
        market_state=MarketState(
            share_reserves=share_reserves,
            init_share_price=simulation_state_.market_state.init_share_price,
            share_price=simulation_state_.market_state.share_price,
        ),
    )
    market_deltas = Wallet(
        d_base_asset=contribution,
        d_token_asset=bond_reserves,
    )
    agent_deltas = Wallet(
        address=wallet_address,
        base=-contribution,
        lp_tokens=2 * bond_reserves + contribution,  # 2y + cz
    )
    return (market_deltas, agent_deltas)


def add_liquidity(
    simulation_state_,
    wallet_address: int,
    trade_amount: float,
) -> tuple[Wallet, Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is added"""
    # get_rate assumes that there is some amount of reserves, and will throw an error if share_reserves is zero
    if (
        simulation_state_.market_state.share_reserves == 0 and simulation_state_.market_state.bond_reserves == 0
    ):  # pool has not been initialized
        rate = 0
    else:
        rate = simulation_state_.apr
    # sanity check inputs
    simulation_state_.pricing_model.check_input_assertions(
        quantity=Quantity(amount=trade_amount, unit=TokenType.PT),  # temporary Quantity object just for this check
        market_state=simulation_state_.market_state,
        time_remaining=simulation_state_.position_duration,
    )
    # perform the trade
    lp_out, d_base_reserves, d_token_reserves = simulation_state_.pricing_model.calc_lp_out_given_tokens_in(
        d_base=trade_amount,
        rate=rate,
        market_state=simulation_state_.market_state,
        time_remaining=simulation_state_.position_duration,
    )
    market_deltas = Wallet(
        d_base_asset=d_base_reserves,
        d_token_asset=d_token_reserves,
        d_lp_reserves=lp_out,
    )
    agent_deltas = Wallet(
        address=wallet_address,
        base=-d_base_reserves,
        lp_tokens=lp_out,
    )
    return market_deltas, agent_deltas


def remove_liquidity(
    simulation_state_,
    wallet_address: int,
    trade_amount: float,
) -> tuple[Wallet, Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is removed"""
    # sanity check inputs
    simulation_state_.pricing_model.check_input_assertions(
        quantity=Quantity(amount=trade_amount, unit=TokenType.PT),  # temporary Quantity object just for this check
        market_state=simulation_state_.market_state,
        time_remaining=simulation_state_.position_duration,
    )
    # perform the trade
    lp_in, d_base_reserves, d_token_reserves = simulation_state_.pricing_model.calc_tokens_out_given_lp_in(
        lp_in=trade_amount,
        rate=simulation_state_.apr,
        market_state=simulation_state_.market_state,
        time_remaining=simulation_state_.position_duration,
    )
    market_deltas = Wallet(
        d_base_asset=-d_base_reserves,
        d_token_asset=-d_token_reserves,
        d_lp_reserves=-lp_in,
    )
    agent_deltas = Wallet(
        address=wallet_address,
        base=d_base_reserves,
        lp_tokens=-lp_in,
    )
    return market_deltas, agent_deltas


def log_market_step_string(simulation_state_) -> None:
    """Logs the current market step"""
    # TODO: This is a HACK to prevent test_sim from failing on market shutdown
    # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
    if simulation_state_.market_state.share_reserves <= 0:
        spot_price = str(np.nan)
        rate = str(np.nan)
    else:
        spot_price = simulation_state_.spot_price
        rate = simulation_state_.apr
    logging.debug(
        ("t = %g" "\nx = %g" "\ny = %g" "\nlp = %g" "\nz = %g" "\nx_b = %g" "\ny_b = %g" "\np = %s" "\npool apr = %s"),
        simulation_state_.time,
        simulation_state_.market_state.share_reserves * simulation_state_.market_state.share_price,
        simulation_state_.market_state.bond_reserves,
        simulation_state_.market_state.lp_reserves,
        simulation_state_.market_state.share_reserves,
        simulation_state_.market_state.base_buffer,
        simulation_state_.market_state.bond_buffer,
        str(spot_price),
        str(rate),
    )


def get_market(
    pricing_model: PricingModel,
    config: Config,
    init_target_liquidity: float = 1.0,
) -> Market:
    r"""Setup market

    Parameters
    ----------
    pricing_model : PricingModel
        instantiated pricing model
    config: Config
        instantiated config object. The following attributes are used:
            init_share_price : float
                the initial price of the yield bearing vault shares
            num_position_days : int
                how much time between token minting and expiry, in days
            redemption_fee_percent : float
                portion of redemptions to be collected as fees for LPers, expressed as a decimal
            target_pool_apr : float
                target apr, used for calculating the time stretch
            trade_fee_percent : float
                portion of trades to be collected as fees for LPers, expressed as a decimal
            vault_apr : list
                valut apr per day for the duration of the simulation
    init_target_liquidity : float = 1.0
        initial liquidity for setting up the market
        should be a tiny amount for setting up apr

    Returns
    -------
    Market
        instantiated market without any liquidity (i.e. no shares or bonds)
    """
    position_duration = StretchedTime(
        days=config.num_position_days,
        time_stretch=pricing_model.calc_time_stretch(config.target_pool_apr),
        normalizing_constant=config.num_position_days,
    )
    # apr is "annual", so if position durations is not 365
    # then we need to rescale the target apr passed to calc_liquidity
    adjusted_target_apr = config.target_pool_apr * config.num_position_days / 365
    share_reserves_direct, bond_reserves_direct = pricing_model.calc_liquidity(
        market_state=MarketState(share_price=config.init_share_price, init_share_price=config.init_share_price),
        target_liquidity=init_target_liquidity,
        target_apr=adjusted_target_apr,
        position_duration=position_duration,
    )
    return Market(
        pricing_model=pricing_model,
        market_state=MarketState(
            share_reserves=share_reserves_direct,
            bond_reserves=bond_reserves_direct,
            base_buffer=0,
            bond_buffer=0,
            lp_reserves=init_target_liquidity / config.init_share_price,
            init_share_price=config.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=config.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
            variable_rate=config.variable_rate[0],  # yield bearing source apr
            trade_fee_percent=config.trade_fee_percent,  # g
            redemption_fee_percent=config.redemption_fee_percent,
        ),
        position_duration=position_duration,
    )


@dataclass
class SimulationState:
    """stores Simulator State"""

    config: Config = field(default_factory=lambda: Config())  # pylint: disable=unnecessary-lambda
    logging.info("%s", config)
    market_state: MarketState = field(default_factory=lambda: MarketState())  # pylint: disable=unnecessary-lambda
    agents: dict[int, Agent] = field(default_factory=dict)

    # Simulation variables
    run_number = [0]
    block_number = [0]
    seconds_in_a_day = 86400
    run_trade_number = [0]

    def __post_init__(self):
        self.time_between_blocks = self.seconds_in_a_day / self.config.num_blocks_per_day
        self.config.check_variable_rate()
        self.config.freeze()  # pylint: disable=no-member # type: ignore
        self.rng = self.config.rng
        logging.info("%s %s %s", "#" * 20, self.config.pricing_model_name, "#" * 20)
        if self.config.pricing_model_name.lower() == "hyperdrive":
            pricing_model = HyperdrivePricingModel()
        elif self.config.pricing_model_name.lower() == "yieldspace":
            pricing_model = YieldSpacePricingModel()
        else:
            raise ValueError(
                f'pricing_config.pricing_model_name must be "Hyperdrive", or "YieldSpace", not {self.config.pricing_model_name}'
            )
        self.market = get_market(pricing_model=pricing_model, config=self.config)
        # Instantiate the market.
        market = get_market(pricing_model, self.config)
        if self.config.init_lp is True:  # Instantiate and add the initial LP agent, if desired
            current_market_liquidity = market.pricing_model.calc_total_liquidity_from_reserves_and_price(
                market_state=self.market_state, share_price=market.market_state.share_price
            )
            lp_amount = self.config.target_liquidity - current_market_liquidity
            init_lp_agent = import_module("elfpy.policies.init_lp").Policy(wallet_address=0, budget=lp_amount)
            self.agents.update({0: init_lp_agent})
        collect_and_execute_trades(simulation_state_=self)  # Initialize the simulator using only the initial LP
        self.agents.update(setup_agents(self.config))


def validate_custom_parameters(policy_instruction):
    """separate the policy name from the policy arguments and validate the arguments"""
    policy_name, policy_args = policy_instruction.split(":")
    try:
        policy_args = policy_args.split(",")
    except AttributeError as exception:
        logging.info("ERROR: No policy arguments provided")
        raise exception
    try:
        policy_args = [arg.split("=") for arg in policy_args]
    except AttributeError as exception:
        logging.info("ERROR: Policy arguments must be provided as key=value pairs")
        raise exception
    try:
        kwargs = {key: float(value) for key, value in policy_args}
    except ValueError as exception:
        logging.info("ERROR: Policy arguments must be provided as key=value pairs")
        raise exception
    return policy_name, kwargs


def setup_agents(config, agent_policies=None) -> dict[int, Agent]:
    """setup agents"""
    agent_policies = config.agent_policies if agent_policies is None else agent_policies
    agents = {}
    for agent_id, policy_instruction in enumerate(agent_policies):
        if ":" in policy_instruction:  # we have custom parameters
            policy_name, not_kwargs = validate_custom_parameters(policy_instruction)
        else:  # we don't have custom parameters
            policy_name = policy_instruction
            not_kwargs = {}
        wallet_address = agent_id + 1
        policy = import_module("elfpy.policies.{policy_name}").Policy
        agent = policy(wallet_address=wallet_address, budget=1000)  # first policy goes to init_lp_agent
        for key, value in not_kwargs.items():
            if hasattr(agent, key):  # check if parameter exists
                setattr(agent, key, value)
            else:
                raise AttributeError(f"Policy {policy_name} does not have parameter {key}")
        agent.log_status_report()
        agents[wallet_address] = agent
    return agents


def collect_trades(simulation_state_, agent_ids: list[int], liquidate: bool = False) -> list[tuple[int, MarketAction]]:
    r"""Collect trades from a set of provided agent IDs.

    Parameters
    ----------
    agent_ids: list[int]
        A list of agent IDs. These IDs must correspond to agents that are
        registered in the simulator.

    liquidate: bool
        If true, have agents collect their liquidation trades. Otherwise, agents collect their normal trades.


    Returns
    -------
    list[tuple[int, MarketAction]]
        A list of trades associated with specific agents.
    """
    agents_and_trades = []
    for agent_id in agent_ids:
        agent = simulation_state_.agents[agent_id]
        if liquidate:
            logging.debug("Collecting liquiditation trades for market closure")
            trades = agent.get_liquidation_trades(simulation_state_.market)
        else:
            trades = agent.get_trades(simulation_state_.market)
        agents_and_trades.extend((agent_id, trade) for trade in trades)
    return agents_and_trades


def collect_and_execute_trades(simulation_state_, last_block_in_sim: bool = False) -> None:
    r"""Get trades from the agent list, execute them, and update states

    Parameters
    ----------
    last_block_in_sim : bool
        If True, indicates if the current set of trades are occuring on the final block in the simulation
    """
    if simulation_state_.config.shuffle_users:
        if last_block_in_sim:
            agent_ids: list[int] = simulation_state_.rng.permutation(  # shuffle wallets except init_lp
                [key for key in simulation_state_.agents if key > 0]  # exclude init_lp before shuffling
            ).tolist()
            if simulation_state_.config.init_lp:
                agent_ids.append(0)  # add init_lp so that they're always last
        else:
            agent_ids = simulation_state_.rng.permutation(
                list(simulation_state_.agents)
            ).tolist()  # random permutation of keys (agent wallet addresses)
    else:  # we are in a deterministic mode
        agent_ids = (
            list(simulation_state_.agents)[
                ::-1
            ]  # close their trades in reverse order to allow withdrawing of LP tokens
            if last_block_in_sim
            else list(simulation_state_.agents)  # execute in increasing order
        )
    agent_trades = collect_trades(simulation_state_, agent_ids, liquidate=last_block_in_sim)
    for trade in agent_trades:
        agent_id, agent_deltas, market_deltas = simulation_state_.market.trade_and_update(trade)
        simulation_state_.market.update_market(market_deltas)
        agent = simulation_state_.agents[agent_id]
        logging.debug(
            "agent #%g wallet deltas:\n%s",
            agent.wallet.address,
            agent_deltas,
        )
        agent.update_wallet(agent_deltas, simulation_state_.market)
        # TODO: Get simulator, market, pricing model, agent state strings and log
        agent.log_status_report()
        # TODO: need to log deaggregated trade informaiton, i.e. trade_deltas
        # issue #215
        update_simulation_state(simulation_state_)
        simulation_state_.run_trade_number += 1


def run_simulation(simulation_state_, liquidate_on_end: bool = True) -> None:
    r"""Run the trade simulation and update the output state dictionary

    This is the primary function of the Simulator class.
    The PricingModel and Market objects will be constructed.
    A loop will execute a group of trades with random volumes and directions for each day,
    up to `self.config.num_trading_days` days.

    Parameters
    ----------
    liquidate_on_end : bool
        if True, liquidate trades when the simulation is complete

    Returns
    -------
    There are no returns, but the function does update the simulation_state member variable
    """
    last_block_in_sim = False
    simulation_state_.start_time = time_utils.current_datetime()
    for day in range(simulation_state_.config.num_trading_days):
        simulation_state_.day = day
        simulation_state_.market.market_state.vault_apr = simulation_state_.config.vault_apr[simulation_state_.day]
        # Vault return can vary per day, which sets the current price per share
        if simulation_state_.day > 0:  # Update only after first day (first day set to init_share_price)
            if simulation_state_.config.compound_vault_apr:  # Apply return to latest price (full compounding)
                price_multiplier = simulation_state_.market.market_state.share_price
            else:  # Apply return to starting price (no compounding)
                price_multiplier = simulation_state_.market.market_state.init_share_price
            delta = Wallet(
                d_share_price=(
                    simulation_state_.market.market_state.vault_apr  # current day's apy
                    / 365  # convert annual yield to daily
                    * price_multiplier
                )
            )
            simulation_state_.market.update_market(delta)
        for daily_block_number in range(simulation_state_.config.num_blocks_per_day):
            simulation_state_.daily_block_number = daily_block_number
            last_block_in_sim = (simulation_state_.day == simulation_state_.config.num_trading_days - 1) and (
                simulation_state_.daily_block_number == simulation_state_.config.num_blocks_per_day - 1
            )
            liquidate = last_block_in_sim and liquidate_on_end
            simulation_state_.collect_and_execute_trades(liquidate)
            logging.debug(
                "day = %d, daily_block_number = %d\n", simulation_state_.day, simulation_state_.daily_block_number
            )
            simulation_state_.market.log_market_step_string()
            if not last_block_in_sim:
                simulation_state_.market.time += simulation_state_.market_step_size()
                simulation_state_.block_number += 1
    # simulation has ended
    for agent in simulation_state_.agents.values():
        agent.log_final_report(simulation_state_.market)


def update_simulation_state(simulation_state_) -> None:
    r"""Increment the list for each key in the simulation_state output variable

    .. todo:: This gets duplicated in notebooks when we make the pandas dataframe.
        Instead, the simulation_state should be a dataframe.
        issue #215
    """
    # pylint: disable=too-many-statements
    parameter_list = [
        "model_name",
        "run_number",
        "day",
        "block_number",
        "market_time",
        "run_trade_number",
        "market_step_size",
        "position_duration",
        "fixed_apr",
        "variable_rate",
    ]
    for parameter in parameter_list:
        if not hasattr(simulation_state_, parameter):
            setattr(simulation_state_, parameter, [])
    simulation_state_.model_name.append(simulation_state_.market.pricing_model.model_name())
    simulation_state_.run_number.append(simulation_state_.run_number)
    simulation_state_.day.append(simulation_state_.day)
    simulation_state_.block_number.append(simulation_state_.block_number)
    simulation_state_.market_time.append(simulation_state_.market.time)
    simulation_state_.run_trade_number.append(simulation_state_.run_trade_number)
    simulation_state_.market_step_size.append(simulation_state_.market_step_size)
    simulation_state_.position_duration.append(simulation_state_.market.position_duration)
    simulation_state_.fixed_apr.append(simulation_state_.market.apr)
    simulation_state_.variable_rate.append(simulation_state_.config.variable_rate[simulation_state_.day])
    simulation_state_.add_dict_entries({f"config.{key}": val for key, val in simulation_state_.config.__dict__.items()})
    simulation_state_.add_dict_entries(simulation_state_.market.market_state.__dict__)
    for agent in simulation_state_.agents.values():
        simulation_state_.add_dict_entries(agent.wallet.get_state(simulation_state_.market))
    # TODO: This is a HACK to prevent test_sim from failing on market shutdown
    # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
    if simulation_state_.market.market_state.share_reserves > 0:  # there is money in the market
        simulation_state_.spot_price.append(simulation_state_.market.spot_price)
    else:
        simulation_state_.spot_price.append(np.nan)


if __name__ == "__main__":
    simulation_state = SimulationState()
    print(f"{simulation_state=}")
    run_simulation(simulation_state_=simulation_state)
