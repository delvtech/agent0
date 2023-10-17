"""Agent policy for LP trading that also arbitrage on the fixed rate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy.types import MarketType, Trade

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveInterface
    from numpy.random._generator import Generator as NumpyGenerator

    from agent0.hyperdrive.state import HyperdriveWallet

from decimal import Decimal, getcontext
import time

# pylint: disable=too-many-parameters, too-many-local-variables

# constants
dec0 = Decimal(0)
dec1 = Decimal(1)
dec2 = Decimal(2)
dec12 = Decimal(12)
dec_seconds_in_year = Decimal(365 * 24 * 60 * 60)
tolerance = Decimal(1e-18)
PRECISION = 24
MAX_ITER = 10


# functions
def calc_bond_reserves(
    share_reserves: Decimal,
    share_price: Decimal,
    target_rate: Decimal,
    position_duration: Decimal,
    time_stretch: Decimal,
):
    """Calculate the amount of bonds that hit the target target rate for the given shares.

    Parameters
    ----------
    share_reserves : Decimal
        The amount of share reserves.
    share_price : Decimal
        The price of the share.
    target_rate : Decimal
        The target rate.
    position_duration : Decimal
        The duration of the position.
    time_stretch : Decimal
        The time stretch factor.

    Returns
    -------
    Decimal
        The amount of bonds that hit the target rate.
    """
    return (
        share_price * share_reserves * ((dec1 + target_rate * position_duration / dec_seconds_in_year) ** time_stretch)
    )


def calc_spot_price_local(
    initial_share_price: Decimal,
    share_reserves: Decimal,
    share_adjustment: Decimal,
    bond_reserves: Decimal,
    time_stretch: Decimal,
) -> Decimal:
    """Calculate spot price.

    Parameters
    ----------
    initial_share_price : Decimal
        The initial price of the share.
    share_reserves : Decimal
        The amount of share reserves.
    share_adjustment : Decimal
        The amount of share adjustment.
    bond_reserves : Decimal
        The amount of bond reserves.
    time_stretch : Decimal
        The time stretch factor.

    Returns
    -------
    Decimal
        The spot price.
    """
    effective_share_reserves = share_reserves - share_adjustment
    return (initial_share_price * effective_share_reserves / bond_reserves) ** time_stretch


def calc_apr(
    share_reserves: Decimal,
    share_adjustment: Decimal,
    bond_reserves: Decimal,
    initial_share_price: Decimal,
    position_duration_seconds: Decimal,
    time_stretch: Decimal,
) -> Decimal:
    """Calculate APR.

    Parameters
    ----------
    share_reserves : Decimal
        The amount of share reserves.
    share_adjustment : Decimal
        The adjustment for share reserves.
    bond_reserves : Decimal
        The amount of bond reserves.
    initial_share_price : Decimal
        The initial price of the share.
    position_duration_seconds : Decimal
        The duration of the position, in seconds.
    time_stretch : Decimal
        The time stretch factor.

    Returns
    -------
    Decimal
        The APR.
    """
    annualized_time = position_duration_seconds / dec_seconds_in_year
    spot_price = calc_spot_price_local(
        initial_share_price, share_reserves, share_adjustment, bond_reserves, time_stretch
    )
    return (dec1 - spot_price) / (spot_price * annualized_time)


def calc_k(
    share_price: Decimal,
    initial_share_price: Decimal,
    share_reserves: Decimal,
    bond_reserves: Decimal,
    time_stretch: Decimal,
) -> Decimal:
    """Calculate the AMM invariant.

    Uses the following equation:
        k_t = (c / mu) * (mu * z) ** (1 - t) + y ** (1 - t)

    Parameters
    ----------
    share_price : Decimal
        The price of the share.
    initial_share_price : Decimal
        The initial price of the share.
    share_reserves : Decimal
        The amount of share reserves.
    bond_reserves : Decimal
        The amount of bond reserves.
    time_stretch : Decimal
        The time stretch factor.

    Returns
    -------
    Decimal
        The AMM invariant.
    """
    return (share_price / initial_share_price) * (initial_share_price * share_reserves) ** (
        dec1 - time_stretch
    ) + bond_reserves ** (dec1 - time_stretch)


def get_shares_in_for_bonds_out(
    bond_reserves,
    share_price,
    initial_share_price,
    share_reserves,
    bonds_out,
    time_stretch,
    curve_fee,
    gov_fee,
    one_block_return,
):
    # y_term = (y - out) ** (1 - t)
    # z_val = (k_t - y_term) / (c / mu)
    # z_val = z_val ** (1 / (1 - t))
    # z_val /= mu
    # return z_val - z
    # pylint: disable=too-many-arguments
    k_t = calc_k(
        share_price,
        initial_share_price,
        share_reserves,
        bond_reserves,
        time_stretch,
    )
    y_term = (bond_reserves - bonds_out) ** (dec1 - time_stretch)
    z_val = (k_t - y_term) / (share_price / initial_share_price)
    z_val = z_val ** (dec1 / (dec1 - time_stretch))
    z_val /= initial_share_price
    # z_val *= one_block_return
    spot_price = calc_spot_price_local(initial_share_price, share_reserves, dec0, bond_reserves, time_stretch)
    amount_in_shares = z_val - share_reserves
    price_discount = dec1 - spot_price
    curve_fee_rate = price_discount * curve_fee
    curve_fee_amount_in_shares = amount_in_shares * curve_fee_rate
    gov_fee_amount_in_shares = curve_fee_amount_in_shares * gov_fee
    # applying fees means you pay MORE shares in for the same amount of bonds OUT
    amount_from_user_in_shares = amount_in_shares + curve_fee_amount_in_shares
    return amount_from_user_in_shares, curve_fee_amount_in_shares, gov_fee_amount_in_shares


def get_shares_out_for_bonds_in(
    bond_reserves,
    share_price,
    initial_share_price,
    share_reserves,
    bonds_in,
    time_stretch,
    curve_fee,
    gov_fee,
    one_block_return,
):
    # y_term = (y + in_) ** (1 - t)
    # z_val = (k_t - y_term) / (c / mu)
    # z_val = z_val ** (1 / (1 - t))
    # z_val /= mu
    # return z - z_val if z > z_val else 0.0
    # pylint: disable=too-many-arguments
    k_t = calc_k(
        share_price,
        initial_share_price,
        share_reserves,
        bond_reserves,
        time_stretch,
    )
    y_term = (bond_reserves + bonds_in) ** (dec1 - time_stretch)
    z_val = (k_t - y_term) / (share_price / initial_share_price)
    z_val = z_val ** (dec1 / (dec1 - time_stretch))
    z_val /= initial_share_price
    # z_val *= one_block_return
    spot_price = calc_spot_price_local(initial_share_price, share_reserves, dec0, bond_reserves, time_stretch)
    price_discount = dec1 - spot_price
    amount_in_shares = max(dec0, share_reserves - z_val)
    curve_fee_rate = price_discount * curve_fee
    curve_fee_amount_in_shares = amount_in_shares * curve_fee_rate
    gov_fee_amount_in_shares = curve_fee_amount_in_shares * gov_fee
    # applying fee means you get LESS shares out for the same amount of bonds IN
    amount_to_user_in_shares = amount_in_shares - curve_fee_amount_in_shares
    return amount_to_user_in_shares, curve_fee_amount_in_shares, gov_fee_amount_in_shares


def calc_reserves_to_hit_target_rate(target_rate: Decimal, interface: HyperdriveInterface) -> tuple[Decimal, Decimal]:
    """Calculate bonds needed to hit target rate.

    Parameters
    ----------
    target_rate : Decimal
        The target rate.
    interface : HyperdriveInterface
        The Hyperdrive API interface object.
    """
    # variables
    predicted_rate = dec0
    pool_config = interface.pool_config.copy()
    pool_info = interface.pool_info.copy()

    pool_info["shareReserves"] = Decimal(str(pool_info["shareReserves"]))
    pool_config["initialSharePrice"] = Decimal(str(pool_config["initialSharePrice"]))
    pool_config["positionDuration"] = Decimal(str(pool_config["positionDuration"]))
    pool_config["timeStretch"] = Decimal(str(pool_config["timeStretch"]))
    pool_config["invTimeStretch"] = Decimal(str(pool_config["invTimeStretch"]))
    pool_info["bondReserves"] = Decimal(str(pool_info["bondReserves"]))
    pool_info["sharePrice"] = Decimal(str(pool_info["sharePrice"]))
    pool_config["curveFee"] = Decimal(str(pool_config["curveFee"]))
    pool_config["governanceFee"] = Decimal(str(pool_config["governanceFee"]))
    fixed_rate = Decimal(str(interface.fixed_rate))
    variable_rate = interface.variable_rate  # this is a Decimal to begin with, unlike every other variable
    assert isinstance(variable_rate, Decimal)
    getcontext().prec = PRECISION
    one_block_return = (dec1 + variable_rate) ** (
        dec12 / dec_seconds_in_year
    )  # attempt to see if this improves accuracy, it's 1e-8 difference

    iteration = 0
    start_time = time.time()
    total_shares_needed = dec0
    total_bonds_needed = dec0
    while abs(predicted_rate - target_rate) > tolerance:  # max tolerance 1e-16
        iteration += 1
        target_bonds = calc_bond_reserves(
            pool_info["shareReserves"],
            pool_config["initialSharePrice"],
            target_rate,
            pool_config["positionDuration"],
            pool_config["invTimeStretch"],
        )
        bonds_needed = (target_bonds - pool_info["bondReserves"]) / dec2
        if bonds_needed > 0:  # handle the short case
            shares_out, curve_fee, gov_fee = get_shares_out_for_bonds_in(
                pool_info["bondReserves"],
                pool_info["sharePrice"],
                pool_config["initialSharePrice"],
                pool_info["shareReserves"],
                bonds_needed,
                pool_config["timeStretch"],
                pool_config["curveFee"],
                pool_config["governanceFee"],
                one_block_return,
            )
            # shares_out is what the user takes OUT: curve_fee less due to fees.
            # gov_fee of that doesn't stay in the pool, going OUT to governance (same direction as user flow).
            pool_info["shareReserves"] += (-shares_out - gov_fee) * 1
        else:  # handle the long case
            shares_in, curve_fee, gov_fee = get_shares_in_for_bonds_out(
                pool_info["bondReserves"],
                pool_info["sharePrice"],
                pool_config["initialSharePrice"],
                pool_info["shareReserves"],
                -bonds_needed,
                pool_config["timeStretch"],
                pool_config["curveFee"],
                pool_config["governanceFee"],
                one_block_return,
            )
            print(f"{shares_in=}")
            print(f"{curve_fee=}")
            print(f"{gov_fee=}")
            # shares_in is what the user pays IN: curve_fee more due to fees.
            # gov_fee of that doesn't go to the pool, going OUT to governance (opposite direction of user flow).
            pool_info["shareReserves"] += (shares_in - gov_fee) * 1  #
        pool_info["bondReserves"] += bonds_needed
        total_shares_needed = pool_info["shareReserves"] - Decimal(str(interface.pool_info["shareReserves"]))
        total_bonds_needed = pool_info["bondReserves"] - Decimal(str(interface.pool_info["bondReserves"]))
        predicted_rate = calc_apr(
            pool_info["shareReserves"],
            dec0,
            pool_info["bondReserves"],
            pool_config["initialSharePrice"],
            pool_config["positionDuration"],
            pool_config["timeStretch"],
        )
        print(
            f"iteration {iteration:3}: {float(predicted_rate):22.18%} d_bonds={float(total_bonds_needed):27,.18f} d_shares={float(total_shares_needed):27,.18f}"
        )
        if iteration >= MAX_ITER:
            break
    print(f"predicted precision: {float(abs(predicted_rate-target_rate))}, time taken: {time.time() - start_time}s")
    return total_shares_needed, total_bonds_needed


# TODO this should maybe subclass from arbitrage policy, but perhaps making it swappable
class LPandArb(HyperdrivePolicy):
    """LP and Arbitrage in a fixed proportion."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
        A description of the policy
        """
        raw_description = """
        LP and arbitrage in a fixed proportion.
        If no arb opportunity, that portion is LPed. In the future this could go into the yield source.
        Try to redeem withdrawal shares right away.
        Arbitrage logic is as follows:
        - If the fixed rate is higher than `high_fixed_rate_thresh`:
            - Close entire short and open a new long for `trade_amount` base.
        - If the fixed rate is lower than `low_fixed_rate_thresh`:
            - Close entire long and open a new short for `trade_amount` bonds.
        """
        return super().describe(raw_description)

    @dataclass
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy.

        Attributes
        ----------
        high_fixed_rate_thresh: FixedPoint
            The upper threshold of the fixed rate to open a position
        low_fixed_rate_thresh: FixedPoint
            The lower threshold of the fixed rate to open a position
        lp_portion: FixedPoint
            The portion of capital assigned to LP
        """

        lp_portion: FixedPoint = FixedPoint("0.5")
        high_fixed_rate_thresh: FixedPoint = FixedPoint("0.1")
        low_fixed_rate_thresh: FixedPoint = FixedPoint("0.02")
        rate_slippage: FixedPoint = FixedPoint("0.01")

        @property
        def arb_portion(self) -> FixedPoint:
            """The portion of capital assigned to arbitrage."""
            return FixedPoint(1) - self.lp_portion

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        policy_config: Config | None = None,
    ):
        """Initialize the bot.

        Arguments
        ---------
        budget: FixedPoint
            The budget of this policy
        rng: NumpyGenerator | None
            Random number generator
        slippage_tolerance: FixedPoint | None
            Slippage tolerance of trades
        policy_config: Config | None
            The custom arguments for this policy
        """
        # Defaults
        if policy_config is None:
            policy_config = self.Config()
        self.policy_config = policy_config
        self.arb_amount = self.policy_config.arb_portion * budget
        self.lp_amount = (self.policy_config.lp_portion) * budget
        self.minimum_trade_amount = FixedPoint("10")
        # calculate these once
        self.fp0 = FixedPoint(0)
        self.fp1 = FixedPoint(1)
        self.fp365 = FixedPoint(365)

        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, interface: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

        Arguments
        ---------
        market : HyperdriveMarketState
            the trading market
        interface : MarketInterface
            Interface for the market on which this agent will be executing trades (MarketActions)
        wallet : HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # Get fixed and variable rates
        fixed_rate = interface.fixed_rate

        action_list = []

        # Initial conditions, open LP position
        if wallet.lp_tokens == FixedPoint(0):
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=self.lp_amount,
                        wallet=wallet,
                        min_apr=fixed_rate - self.policy_config.rate_slippage,
                        max_apr=fixed_rate + self.policy_config.rate_slippage,
                    ),
                )
            )

        # arbitrage from here on out
        high_fixed_rate_detected = fixed_rate >= self.policy_config.high_fixed_rate_thresh
        print(f"{high_fixed_rate_detected=}")
        low_fixed_rate_detected = fixed_rate <= self.policy_config.low_fixed_rate_thresh
        print(f"{low_fixed_rate_detected=}")
        we_have_money = wallet.balance.amount > self.minimum_trade_amount
        print(f"{we_have_money=}")

        shares_needed, bonds_needed = None, None
        if we_have_money:
            if high_fixed_rate_detected or low_fixed_rate_detected:
                shares_needed, bonds_needed = calc_reserves_to_hit_target_rate(
                    target_rate=Decimal(str(interface.variable_rate)),
                    interface=interface,
                )

        # Close longs if matured
        for maturity_time, long in wallet.longs.items():
            # If matured
            if maturity_time < interface.current_block_time:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            wallet=wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )
        # Close shorts if matured
        for maturity_time, short in wallet.shorts.items():
            # If matured
            if maturity_time < interface.current_block_time:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            wallet=wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )

        # High fixed rate detected
        if high_fixed_rate_detected:
            # Close all open shorts
            if len(wallet.shorts) > 0:
                for maturity_time, short in wallet.shorts.items():
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_SHORT,
                                trade_amount=short.balance,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new long, if we have money
            if we_have_money:
                shares_needed, bonds_needed = calc_reserves_to_hit_target_rate(
                    target_rate=target_rate,
                    interface=interface,
                )
                max_long_bonds = interface.get_max_long(wallet.balance.amount)
                max_long_shares = get_shares_in_for_bonds_out(
                    interface.pool_info["bondReserves"],
                    interface.pool_info["sharePrice"],
                    interface.pool_config["initialSharePrice"],
                    interface.pool_info["shareReserves"],
                    max_long_bonds,
                    interface.pool_config["timeStretch"],
                )
                amount = min(shares_needed, max_long_shares) * interface.pool_info["sharePrice"]
                print(f"{max_long_shares=}")
                print(f"{amount=}")
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.OPEN_LONG,
                            trade_amount=amount,
                            wallet=wallet,
                        ),
                    )
                )

        # Low fixed rate detected
        if low_fixed_rate_detected:
            # Close all open longs
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_LONG,
                                trade_amount=long.balance,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new short, if we have money
            if we_have_money:
                max_short_bonds = interface.get_max_short(wallet.balance.amount)
                amount = min(bonds_needed, max_short_bonds)
                print(f"{max_short_bonds=}")
                print(f"{amount=}")
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.OPEN_SHORT,
                            trade_amount=amount,
                            wallet=wallet,
                        ),
                    )
                )

        return action_list, False
