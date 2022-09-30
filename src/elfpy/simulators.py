"""
Simulator class wraps the pricing models and markets
for experiment tracking and execution
"""

import numpy as np

from elfipy.markets import Market
from elfipy.pricing_models import ElementPricingModel
from elfipy.pricing_models import YieldSpacev2PricingModel


class YieldSimulator:
    """
    Stores environment varialbes & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes
    """
    # TODO: set up member object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(self, **kwargs):
        # TODO: Move away from using kwargs (this was a hack and can introduce bugs if the dict gets updated)
        #       Better to do named & typed args w/ defaults
        # percentage of the slippage we take as a fee
        self.min_fee = kwargs.get("min_fee")
        self.max_fee = kwargs.get("max_fee")
        self.floor_fee = kwargs.get("floor_fee")  # minimum fee we take
        # tokens to be traded
        self.tokens = kwargs.get("tokens")  # list of strings
        self.min_target_liquidity = kwargs.get("min_target_liquidity")
        self.max_target_liquidity = kwargs.get("max_target_liquidity")
        self.min_target_volume = kwargs.get("min_target_volume")
        self.max_target_volume = kwargs.get("max_target_volume")
        self.min_pool_apy = kwargs.get("min_pool_apy")
        self.max_pool_apy = kwargs.get("max_pool_apy")
        self.min_vault_age = kwargs.get("min_vault_age")
        self.max_vault_age = kwargs.get("max_vault_age")
        self.min_vault_apy = kwargs.get("min_vault_apy")
        self.max_vault_apy = kwargs.get("max_vault_apy")
        self.base_asset_price = kwargs.get("base_asset_price")
        self.precision = kwargs.get("precision")
        self.pricing_model_name = str(kwargs.get("pricing_model_name"))
        self.trade_direction = kwargs.get("trade_direction")
        self.pool_duration = kwargs.get("pool_duration")
        self.num_trading_days = kwargs.get("num_trading_days")
        self.rng = kwargs.get("rng")
        self.verbose = kwargs.get("verbose")
        self.run_number = 0
        self.run_trade_number = 0
        # Random variables
        self.target_liquidity = None
        self.target_daily_volume = None
        self.init_pool_apy = None
        self.fee_percent = None
        self.init_vault_age = None
        self.vault_apy = None
        # Simulation variables
        self.day = 0
        self.init_time_stretch = 1
        self.init_share_price = None
        self.time_stretch = None
        self.pricing_model = None
        self.market = None
        self.step_size = None
        self.trade_amount = None
        self.trade_amount_usd = None
        self.token_in = None
        self.token_out = None
        self.without_fee_or_slippage = None
        self.with_fee = None
        self.without_fee = None
        self.fee = None
        self.random_variables_set = False
        # Output keys, used for logging on a trade-by-trade basis
        analysis_keys = [
            "run_number",
            "model_name",
            "time_until_end",
            "days_until_end",
            "init_time_stretch",
            "target_liquidity",
            "target_daily_volume",
            "pool_apy",
            "fee_percent",
            "floor_fee",
            "init_vault_age",
            "base_asset_price",
            "vault_apy",
            "base_asset_reserves",
            "token_asset_reserves",
            "total_supply",
            "token_in",
            "token_out",
            "trade_direction",
            "trade_amount",
            "trade_amount_usd",
            "share_price",  # c in YieldSpace with Yield Bearing Vaults
            "init_share_price",  # u in YieldSpace with Yield Bearing Vaults
            "out_without_fee_slippage",
            "out_with_fee",
            "out_without_fee",
            "fee",
            "slippage",
            "pool_duration",
            "num_trading_days",
            "day",
            "run_trade_number",
            "spot_price",
            "num_orders",
            "step_size",
        ]
        self.analysis_dict = {key: [] for key in analysis_keys}

    def set_random_variables(self):
        """Use random number generator to assign initial simulation parameter values"""
        self.target_liquidity = self.rng.uniform(
            self.min_target_liquidity, self.max_target_liquidity
        )
        self.target_daily_volume = self.rng.uniform(
            self.min_target_volume, self.max_target_volume
        )
        self.init_pool_apy = self.rng.uniform(
            self.min_pool_apy, self.max_pool_apy
        )  # starting fixed apr
        self.fee_percent = self.rng.uniform(self.min_fee, self.max_fee)
        # Determine real-world parameters for estimating initial (u) and current (c) price-per-share
        self.init_vault_age = self.rng.uniform(
            self.min_vault_age, self.max_vault_age
        )  # in years
        self.vault_apy = self.rng.uniform(
            self.min_vault_apy, self.max_vault_apy, size=self.num_trading_days
        )
        self.vault_apy /= 100  # as a decimal
        self.random_variables_set = True

    def print_random_variables(self):
        """Prints all variables that are set in set_random_variables()"""
        print(
            "Simulation random variables:\n"
            + f"target_liquidity: {self.target_liquidity}\n"
            + f"target_daily_volume: {self.target_daily_volume}\n"
            + f"init_pool_apy: {self.init_pool_apy}\n"
            + f"fee_percent: {self.fee_percent}\n"
            + f"init_vault_age: {self.init_vault_age}\n"
            + f"init_vault_apy: {self.vault_apy[0]}\n"  # first element in vault_apy array
        )

    def reset_rng(self, rng):
        """
        Assign the internal random number generator to a new instantiation

        This function is useful for forcing identical trade volume and directions across simulation runs
        """

        assert isinstance(
            rng, type(np.random.default_rng())
        ), f"rng type must be a random number generator, not {type(rng)}."
        self.rng = rng

    def setup_pricing_and_market(self, override_dict=None):
        """Constructs the pricing model and market member variables"""
        # Update parameters if the user provided new ones
        assert (
            self.random_variables_set
        ), "ERROR: You must run simulator.set_random_variables() before running the simulation"
        if override_dict is not None:
            for key in override_dict.keys():
                if hasattr(self, key):
                    setattr(self, key, override_dict[key])
                    if key == "vault_apy":
                        if isinstance(override_dict[key], list):
                            assert len(override_dict[key]) == self.num_trading_days, (
                                f"vault_apy must have len equal to num_trading_days = {self.num_trading_days},"
                                + f" not {len(override_dict[key])}"
                            )
                        else:
                            setattr(
                                self,
                                key,
                                [
                                    override_dict[key],
                                ]
                                * self.num_trading_days,
                            )
        if (
            override_dict is not None and "init_share_price" in override_dict.keys()
        ):  # \mu variable
            self.init_share_price = override_dict["init_share_price"]
        else:
            init_vault_apy_decimal = self.vault_apy[0] / 100
            self.init_share_price = (1 + init_vault_apy_decimal) ** self.init_vault_age
            if self.precision is not None:
                self.init_share_price = np.around(self.init_share_price, self.precision)
        # Initiate pricing model
        if self.pricing_model_name.lower() == "yieldspacev2":
            self.pricing_model = YieldSpacev2PricingModel(self.verbose, self.floor_fee)
        elif self.pricing_model_name.lower() == "element":
            self.pricing_model = ElementPricingModel(self.verbose)
        else:
            raise ValueError(
                f'pricing_model_name must be "YieldSpacev2" or "Element", not {self.pricing_model_name}'
            )
        self.init_time_stretch = self.pricing_model.calc_time_stretch(
            self.init_pool_apy
        )
        init_reserves = self.pricing_model.calc_liquidity(
            self.target_liquidity,
            self.base_asset_price,
            self.init_pool_apy,
            self.pool_duration,
            self.init_time_stretch,
            self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
        )
        init_base_asset_reserves, init_token_asset_reserves = init_reserves[:2]
        init_time_remaining = self.pricing_model.days_to_time_remaining(
            self.pool_duration, self.init_time_stretch
        )
        self.market = Market(
            base_asset=init_base_asset_reserves,  # x
            token_asset=init_token_asset_reserves,  # y
            fee_percent=self.fee_percent,  # g
            time_remaining=init_time_remaining,  # t
            pricing_model=self.pricing_model,
            init_share_price=self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
            verbose=self.verbose,
        )
        step_scale = 1  # TODO: support scaling the step_size via the override dict (i.e. make a step_scale parameter)
        self.step_size = self.pricing_model.days_to_time_remaining(
            step_scale, self.init_time_stretch, normalizing_constant=365
        )

    def run_simulation(self, override_dict=None):
        """
        Run the trade simulation and update the output state dictionary

        Arguments:
        override_dict [dict] Override member variables.
        Keys in this dictionary must match member variables of the YieldSimulator class.

        This is the primary function of the YieldSimulator class.
        The PricingModel and Market objects will be constructed.
        A loop will execute a group of trades with random volumes and directions for each day,
        up to `self.num_trading_days` days.
        """

        self.run_trade_number = 0
        self.setup_pricing_and_market(override_dict)
        self.update_analysis_dict()  # Initial conditions
        for day in range(0, self.num_trading_days):
            self.day = day
            # APY can vary per day, which sets the current price per share.
            # div by 100 to convert percent to decimal;
            # div by 365 to convert annual to daily;
            # market.init_share_price is the value of 1 share
            self.market.share_price += (
                self.vault_apy[self.day] / 100 / 365 * self.market.init_share_price
            )
            # Loop over trades on the given day
            # TODO: adjustable target daily volume that is a function of the day
            # TODO: improve trading dist, simplify  market price conversion, allow for different amounts
            # Could define a 'trade amount & direction' time series that's a function of the vault apy
            # Could support using actual historical trades or a fit to historical trades)
            day_trading_volume = 0
            while day_trading_volume < self.target_daily_volume:
                # Compute tokens to swap
                token_index = self.rng.integers(low=0, high=2)  # 0 or 1
                self.token_in = self.tokens[token_index]
                self.token_out = self.tokens[1 - token_index]
                if self.trade_direction == "in":
                    if self.token_in == "fyt":
                        target_reserves = self.market.token_asset
                    else:
                        target_reserves = self.market.base_asset
                elif self.trade_direction == "out":
                    if self.token_in == "fyt":
                        target_reserves = self.market.base_asset
                    else:
                        target_reserves = self.market.token_asset
                # Compute trade amount, which can't be more than the available reserves.
                trade_mean = self.target_daily_volume / 10
                trade_std = self.target_daily_volume / 100
                self.trade_amount_usd = self.rng.normal(trade_mean, trade_std)
                self.trade_amount_usd = np.minimum(
                    self.trade_amount_usd, target_reserves * self.base_asset_price
                )
                self.trade_amount = (
                    self.trade_amount_usd / self.base_asset_price
                )  # convert to token units
                if self.verbose:
                    print(
                        f"trades={self.market.base_asset_orders + self.market.token_asset_orders} "
                        + f"init_share_price={self.market.init_share_price}, "
                        + f"share_price={self.market.share_price}, "
                        + f"amount={self.trade_amount}, "
                        + f"reserves={(self.market.base_asset, self.market.token_asset)}"
                    )
                # Conduct trade & update state
                (
                    self.without_fee_or_slippage,
                    self.with_fee,
                    self.without_fee,
                    self.fee,
                ) = self.market.swap(
                    self.trade_amount,  # in units of target asset
                    self.trade_direction,  # out or in
                    self.token_in,  # base or fyt
                    self.token_out,  # opposite of token_in
                )
                self.update_analysis_dict()
                day_trading_volume += (
                    self.trade_amount * self.base_asset_price
                )  # track daily volume in USD terms
                self.run_trade_number += 1
            if (
                self.day < self.num_trading_days - 1
            ):  # no need to tick the market after the last day
                self.market.tick(self.step_size)
        self.run_number += 1

    def get_days_remaining(self):
        """Returns the days remaining in the pool"""
        return self.pricing_model.time_to_days_remaining(
            self.market.time_remaining, self.init_time_stretch
        )

    def update_analysis_dict(self):
        """Increment the list for each key in the analysis_dict output variable"""
        # Variables that are constant across runs
        self.analysis_dict["model_name"].append(self.market.pricing_model.model_name())
        self.analysis_dict["run_number"].append(self.run_number)
        self.analysis_dict["time_until_end"].append(self.market.time_remaining)
        self.analysis_dict["init_time_stretch"].append(self.init_time_stretch)
        self.analysis_dict["target_liquidity"].append(self.target_liquidity)
        self.analysis_dict["target_daily_volume"].append(self.target_daily_volume)
        self.analysis_dict["fee_percent"].append(self.market.fee_percent)
        self.analysis_dict["floor_fee"].append(self.floor_fee)
        self.analysis_dict["init_vault_age"].append(self.init_vault_age)
        self.analysis_dict["pool_duration"].append(self.pool_duration)
        self.analysis_dict["num_trading_days"].append(self.num_trading_days)
        self.analysis_dict["step_size"].append(self.step_size)
        self.analysis_dict["init_share_price"].append(self.market.init_share_price)
        # Variables that change per run
        self.analysis_dict["day"].append(self.day)
        self.analysis_dict["num_orders"].append(
            self.market.base_asset_orders + self.market.token_asset_orders
        )
        self.analysis_dict["vault_apy"].append(self.vault_apy[self.day])
        days_remaining = self.get_days_remaining()
        self.analysis_dict["days_until_end"].append(days_remaining)
        self.analysis_dict["pool_apy"].append(self.market.apy(days_remaining))
        # Variables that change per trade
        self.analysis_dict["run_trade_number"].append(self.run_trade_number)
        self.analysis_dict["base_asset_reserves"].append(self.market.base_asset)
        self.analysis_dict["token_asset_reserves"].append(self.market.token_asset)
        self.analysis_dict["total_supply"].append(self.market.total_supply)
        self.analysis_dict["base_asset_price"].append(self.base_asset_price)
        self.analysis_dict["token_in"].append(self.token_in)
        self.analysis_dict["token_out"].append(self.token_out)
        self.analysis_dict["trade_direction"].append(self.trade_direction)
        self.analysis_dict["trade_amount"].append(self.trade_amount)
        self.analysis_dict["trade_amount_usd"].append(self.trade_amount_usd)
        self.analysis_dict["share_price"].append(self.market.share_price)
        if self.fee is None:
            self.analysis_dict["out_without_fee_slippage"].append(None)
            self.analysis_dict["out_with_fee"].append(None)
            self.analysis_dict["out_without_fee"].append(None)
            self.analysis_dict["fee"].append(None)
            self.analysis_dict["slippage"].append(None)
        else:
            self.analysis_dict["out_without_fee_slippage"].append(
                self.without_fee_or_slippage * self.base_asset_price
            )
            self.analysis_dict["out_with_fee"].append(
                self.with_fee * self.base_asset_price
            )
            self.analysis_dict["out_without_fee"].append(
                self.without_fee * self.base_asset_price
            )
            self.analysis_dict["fee"].append(self.fee * self.base_asset_price)
            slippage = (
                self.without_fee_or_slippage - self.without_fee
            ) * self.base_asset_price
            self.analysis_dict["slippage"].append(slippage)
        self.analysis_dict["spot_price"].append(self.market.spot_price())
