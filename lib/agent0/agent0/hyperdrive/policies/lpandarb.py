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

import time

# pylint: disable=too-many-parameters, too-many-local-variables

# constants
fp0 = FixedPoint(0)
fp1 = FixedPoint(1)
fp2 = FixedPoint(2)
fp12 = FixedPoint(12)
fp_seconds_in_year = FixedPoint(365 * 24 * 60 * 60)
tolerance = 1e-18
MAX_ITER = 10
MIN_TRADE_AMOUNT = FixedPoint(scaled_value=20)


# functions
def calc_bond_reserves(
    share_reserves: FixedPoint,
    share_price: FixedPoint,
    target_rate: FixedPoint,
    position_duration: FixedPoint,
    time_stretch: FixedPoint,
):
    """Calculate the amount of bonds that hit the target target rate for the given shares.

    Parameters
    ----------
    share_reserves : FixedPoint
        The amount of share reserves.
    share_price : FixedPoint
        The price of the share.
    target_rate : FixedPoint
        The target rate.
    position_duration : FixedPoint
        The duration of the position.
    time_stretch : FixedPoint
        The time stretch factor.

    Returns
    -------
    FixedPoint
        The amount of bonds that hit the target rate.
    """
    return share_price * share_reserves * ((fp1 + target_rate * position_duration / fp_seconds_in_year) ** time_stretch)


def calc_spot_price_local(
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    share_adjustment: FixedPoint,
    bond_reserves: FixedPoint,
    time_stretch: FixedPoint,
) -> FixedPoint:
    """Calculate spot price.

    Parameters
    ----------
    initial_share_price : FixedPoint
        The initial price of the share.
    share_reserves : FixedPoint
        The amount of share reserves.
    share_adjustment : FixedPoint
        The amount of share adjustment.
    bond_reserves : FixedPoint
        The amount of bond reserves.
    time_stretch : FixedPoint
        The time stretch factor.

    Returns
    -------
    FixedPoint
        The spot price.
    """
    effective_share_reserves = share_reserves - share_adjustment
    return (initial_share_price * effective_share_reserves / bond_reserves) ** time_stretch


def calc_apr(
    share_reserves: FixedPoint,
    share_adjustment: FixedPoint,
    bond_reserves: FixedPoint,
    initial_share_price: FixedPoint,
    position_duration_seconds: FixedPoint,
    time_stretch: FixedPoint,
) -> FixedPoint:
    """Calculate APR.

    Parameters
    ----------
    share_reserves : FixedPoint
        The amount of share reserves.
    share_adjustment : FixedPoint
        The adjustment for share reserves.
    bond_reserves : FixedPoint
        The amount of bond reserves.
    initial_share_price : FixedPoint
        The initial price of the share.
    position_duration_seconds : FixedPoint
        The duration of the position, in seconds.
    time_stretch : FixedPoint
        The time stretch factor.

    Returns
    -------
    FixedPoint
        The APR.
    """
    annualized_time = position_duration_seconds / fp_seconds_in_year
    spot_price = calc_spot_price_local(
        initial_share_price, share_reserves, share_adjustment, bond_reserves, time_stretch
    )
    return (fp1 - spot_price) / (spot_price * annualized_time)


def calc_k(
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    bond_reserves: FixedPoint,
    time_stretch: FixedPoint,
) -> FixedPoint:
    """Calculate the AMM invariant.

    Uses the following equation:
        k_t = (c / mu) * (mu * z) ** (1 - t) + y ** (1 - t)

    Parameters
    ----------
    share_price : FixedPoint
        The price of the share.
    initial_share_price : FixedPoint
        The initial price of the share.
    share_reserves : FixedPoint
        The amount of share reserves.
    bond_reserves : FixedPoint
        The amount of bond reserves.
    time_stretch : FixedPoint
        The time stretch factor.

    Returns
    -------
    FixedPoint
        The AMM invariant.
    """
    return (share_price / initial_share_price) * (initial_share_price * share_reserves) ** (
        fp1 - time_stretch
    ) + bond_reserves ** (fp1 - time_stretch)


def get_shares_in_for_bonds_out(
    bond_reserves: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    bonds_out: FixedPoint,
    time_stretch: FixedPoint,
    curve_fee: FixedPoint,
    gov_fee: FixedPoint,
    one_block_return: FixedPoint | None = None,
) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
    """Calculates the amount of shares a user will receive from the pool by providing a specified amount of bonds.

    Implements the formula:
        y_term = (y - out) ** (1 - t)
        z_val = (k_t - y_term) / (c / mu)
        z_val = z_val ** (1 / (1 - t))
        z_val /= mu
        return z_val - z

    Parameters
    ----------
    bond_reserves : FixedPoint
        The amount of bond reserves.
    share_price : FixedPoint
        The price of a share in the yield source
    initial_share_price : FixedPoint
        The initial price of a share in the yield source.
    share_reserves : FixedPoint
        The amount of share reserves.
    bonds_out : FixedPoint
        The amount of bonds out.
    time_stretch : FixedPoint
        The time stretch factor.
    curve_fee : FixedPoint
        The curve fee.
    gov_fee : FixedPoint
        The governance fee.
    one_block_return : FixedPoint, optional
        An estimate of the variable return expected for the next block, by default None.
    """
    # pylint: disable=too-many-arguments
    if one_block_return is None:
        one_block_return = FixedPoint(1)
    k_t = calc_k(
        share_price,
        initial_share_price,
        share_reserves,
        bond_reserves,
        time_stretch,
    )
    y_term = (bond_reserves - bonds_out) ** (fp1 - time_stretch)
    z_val = (k_t - y_term) / (share_price / initial_share_price)
    z_val = z_val ** (fp1 / (fp1 - time_stretch))
    z_val /= initial_share_price
    # z_val *= one_block_return
    spot_price = calc_spot_price_local(initial_share_price, share_reserves, fp0, bond_reserves, time_stretch)
    amount_in_shares = z_val - share_reserves
    price_discount = fp1 - spot_price
    curve_fee_rate = price_discount * curve_fee
    curve_fee_amount_in_shares = amount_in_shares * curve_fee_rate
    gov_fee_amount_in_shares = curve_fee_amount_in_shares * gov_fee
    # applying fees means you pay MORE shares in for the same amount of bonds OUT
    amount_from_user_in_shares = amount_in_shares + curve_fee_amount_in_shares
    return amount_from_user_in_shares, curve_fee_amount_in_shares, gov_fee_amount_in_shares


def get_shares_out_for_bonds_in(
    bond_reserves: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    bonds_in: FixedPoint,
    time_stretch: FixedPoint,
    curve_fee: FixedPoint,
    gov_fee: FixedPoint,
    one_block_return: FixedPoint | None = None,
):
    """Calculates the amount of shares a user will receive from the pool by providing a specified amount of bonds.

    Implements the formula:
        y_term = (y + in_) ** (1 - t)
        z_val = (k_t - y_term) / (c / mu)
        z_val = z_val ** (1 / (1 - t))
        z_val /= mu
        return z - z_val if z > z_val else 0.0

    Parameters
    ----------
    bond_reserves : FixedPoint
        The amount of bond reserves.
    share_price : FixedPoint
        The price of a share in the yield source
    initial_share_price : FixedPoint
        The initial price of a share in the yield source.
    share_reserves : FixedPoint
        The amount of share reserves.
    bonds_in : FixedPoint
        The amount of bonds in.
    time_stretch : FixedPoint
        The time stretch factor.
    curve_fee : FixedPoint
        The curve fee.
    gov_fee : FixedPoint
        The governance fee.
    one_block_return : FixedPoint, optional
        An estimate of the variable return expected for the next block, by default None.
    """
    # pylint: disable=too-many-arguments
    if one_block_return is None:
        one_block_return = FixedPoint(1)
    k_t = calc_k(
        share_price,
        initial_share_price,
        share_reserves,
        bond_reserves,
        time_stretch,
    )
    y_term = (bond_reserves + bonds_in) ** (fp1 - time_stretch)
    z_val = (k_t - y_term) / (share_price / initial_share_price)
    z_val = z_val ** (fp1 / (fp1 - time_stretch))
    z_val /= initial_share_price
    # z_val *= one_block_return
    spot_price = calc_spot_price_local(initial_share_price, share_reserves, fp0, bond_reserves, time_stretch)
    price_discount = fp1 - spot_price
    amount_in_shares = max(fp0, share_reserves - z_val)
    curve_fee_rate = price_discount * curve_fee
    curve_fee_amount_in_shares = amount_in_shares * curve_fee_rate
    gov_fee_amount_in_shares = curve_fee_amount_in_shares * gov_fee
    # applying fee means you get LESS shares out for the same amount of bonds IN
    amount_to_user_in_shares = amount_in_shares - curve_fee_amount_in_shares
    return amount_to_user_in_shares, curve_fee_amount_in_shares, gov_fee_amount_in_shares


def calc_reserves_to_hit_target_rate(
    target_rate: FixedPoint, interface: HyperdriveInterface
) -> tuple[FixedPoint, FixedPoint]:
    """Calculate bonds needed to hit target rate.

    Arguments
    ---------
    target_rate : Decimal
        The target rate.
    interface : HyperdriveInterface
        The Hyperdrive API interface object.

    Returns
    -------
    tuple[FixedPoint, FixedPoint] containing:
        total_shares_needed : FixedPoint
            Total amount of shares needed to be added into the pool to hit the target rate.
        total_bonds_needed : FixedPoint
            Total amount of bonds needed to be added into the pool to hit the target rate.
    """
    # variables
    predicted_rate = fp0
    pool_config = interface.pool_config.copy()
    pool_info = interface.pool_info.copy()

    variable_rate = interface.variable_rate
    one_block_return = (fp1 + variable_rate) ** (
        fp12 / fp_seconds_in_year
    )  # attempt to see if this improves accuracy, it's 1e-8 difference

    iteration = 0
    start_time = time.time()
    total_shares_needed = fp0
    total_bonds_needed = fp0
    print(f"Targetting {float(target_rate):.2%} from {float(interface.fixed_rate):.2%}")
    while float(abs(predicted_rate - target_rate)) > tolerance:
        iteration += 1
        target_bonds = calc_bond_reserves(
            pool_info["shareReserves"],
            pool_config["initialSharePrice"],
            target_rate,
            pool_config["positionDuration"],
            pool_config["invTimeStretch"],
        )
        bonds_needed = (target_bonds - pool_info["bondReserves"]) / fp2
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
            # shares_in is what the user pays IN: curve_fee more due to fees.
            # gov_fee of that doesn't go to the pool, going OUT to governance (opposite direction of user flow).
            pool_info["shareReserves"] += (shares_in - gov_fee) * 1  #
        pool_info["bondReserves"] += bonds_needed
        total_shares_needed = pool_info["shareReserves"] - interface.pool_info["shareReserves"]
        total_bonds_needed = pool_info["bondReserves"] - interface.pool_info["bondReserves"]
        predicted_rate = calc_apr(
            pool_info["shareReserves"],
            fp0,
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
        interface : HyperdriveInterface
            Interface for the market on which this agent will be executing trades (MarketActions)
        wallet : HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """

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
                        min_apr=interface.fixed_rate - self.policy_config.rate_slippage,
                        max_apr=interface.fixed_rate + self.policy_config.rate_slippage,
                    ),
                )
            )

        # arbitrage from here on out
        high_fixed_rate_detected = interface.fixed_rate >= self.policy_config.high_fixed_rate_thresh
        low_fixed_rate_detected = interface.fixed_rate <= self.policy_config.low_fixed_rate_thresh
        we_have_money = wallet.balance.amount > self.minimum_trade_amount

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
            shares_needed, bonds_needed = calc_reserves_to_hit_target_rate(
                target_rate=interface.variable_rate,
                interface=interface,
            )
            bonds_needed = -bonds_needed  # we trade positive numbers around here
            # Start by reducing shorts
            if len(wallet.shorts) > 0:
                for maturity_time, short in wallet.shorts.items():
                    reduce_short_amount = min(short.balance, bonds_needed)
                    bonds_needed -= reduce_short_amount
                    print(f"reducing short by {reduce_short_amount}")
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_SHORT,
                                trade_amount=reduce_short_amount,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new long, if there's still a need, and we have money
            if we_have_money and bonds_needed > MIN_TRADE_AMOUNT:
                max_long_bonds = interface.get_max_long(wallet.balance.amount)
                max_long_shares, _, _ = get_shares_in_for_bonds_out(
                    interface.pool_info["bondReserves"],
                    interface.pool_info["sharePrice"],
                    interface.pool_config["initialSharePrice"],
                    interface.pool_info["shareReserves"],
                    max_long_bonds,
                    interface.pool_config["timeStretch"],
                    interface.pool_config["curveFee"],
                    interface.pool_config["governanceFee"],
                )
                amount = min(shares_needed, max_long_shares) * interface.pool_info["sharePrice"]
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
            shares_needed, bonds_needed = calc_reserves_to_hit_target_rate(
                target_rate=interface.variable_rate,
                interface=interface,
            )
            print(f"{bonds_needed=}")
            # Start by reducing longs
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    reduce_long_amount = min(long.balance, bonds_needed)
                    bonds_needed -= reduce_long_amount
                    print(f"reducing long by {reduce_long_amount}")
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_LONG,
                                trade_amount=reduce_long_amount,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new short, if there's still a need, and we have money
            if we_have_money and bonds_needed > MIN_TRADE_AMOUNT:
                max_short_bonds = interface.get_max_short(wallet.balance.amount)
                amount = min(bonds_needed, max_short_bonds)
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
