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
        print(f"{fixed_rate=}")
        variable_rate = interface.variable_rate
        print(f"{variable_rate=}")

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

        def calc_bond_reserves(share_reserves, share_price, apr, position_duration, time_stretch):
            return share_price * share_reserves * ((self.fp1 + apr * position_duration / self.fp365) ** time_stretch)

        def k(share_price, initial_share_price, share_reserves, bond_reserves, time_stretch):
            # (c / mu) * (mu * z) ** (1 - t) + y ** (1 - t)
            return (share_price / initial_share_price) * (initial_share_price * share_reserves) ** (
                self.fp1 - time_stretch
            ) + bond_reserves ** (self.fp1 - time_stretch)

        def get_shares_in_for_bonds_out(
            bond_reserves, share_price, initial_share_price, share_reserves, bonds_out, time_stretch
        ):
            # y_term = (y - out) ** (1 - t)
            # z_val = (k_t - y_term) / (c / mu)
            # z_val = z_val ** (1 / (1 - t))
            # z_val /= mu
            # return z_val - z
            # pylint: disable=too-many-arguments
            k_t = k(
                interface.pool_info["sharePrice"],
                interface.pool_config["initialSharePrice"],
                interface.pool_info["shareReserves"],
                interface.pool_info["bondReserves"],
                interface.pool_config["timeStretch"],
            )
            y_term = (bond_reserves - bonds_out) ** (self.fp1 - time_stretch)
            z_val = (k_t - y_term) / (share_price / initial_share_price)
            z_val = z_val ** (self.fp1 / (self.fp1 - time_stretch))
            z_val /= initial_share_price
            return z_val - share_reserves

        shares_needed: FixedPoint = self.fp0
        bonds_needed: FixedPoint = self.fp0
        if we_have_money:
            if high_fixed_rate_detected or low_fixed_rate_detected:
                # Calculate bonds needed to hit target APR
                target_apr = variable_rate
                target_bonds = calc_bond_reserves(
                    interface.pool_info["shareReserves"],
                    interface.pool_config["initialSharePrice"],
                    target_apr,
                    interface.pool_config["positionDuration"],
                    interface.pool_config["timeStretch"],
                )
                print(f"{interface.pool_config['timeStretch']=}")
                bonds_needed = (target_bonds - interface.pool_info["bondReserves"]) / FixedPoint(2)
                print(f"{bonds_needed=}")
            if high_fixed_rate_detected:
                # assert bonds_needed < 0, "To lower the fixed rate, we should require a decrease in bonds"
                shares_needed = get_shares_in_for_bonds_out(
                    interface.pool_info["bondReserves"],
                    interface.pool_info["sharePrice"],
                    interface.pool_config["initialSharePrice"],
                    interface.pool_info["shareReserves"],
                    abs(bonds_needed),
                    interface.pool_config["timeStretch"],
                )
                print(f"{shares_needed=}")

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
                assert shares_needed, "shares_needed is None"
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
