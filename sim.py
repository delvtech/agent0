import numpy as np

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals

class YieldSimulator():
    """
    Stores environment varialbes & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes

    TODO: completely remove calc_in_given_out
    TODO: Move away from using kwargs (this was a hack and can introduce bugs if the dict gets updated)
          Better to do named & typed args w/ defaults
    """

    def __init__(self, **kwargs):
        self.min_fee = kwargs.get('min_fee') # percentage of the slippage we take as a fee
        self.max_fee = kwargs.get('max_fee')
        self.floor_fee = kwargs.get('floor_fee') # minimum fee we take
        self.tokens = kwargs.get('tokens') # list of strings
        self.min_target_liquidity = kwargs.get('min_target_liquidity')
        self.max_target_liquidity = kwargs.get('max_target_liquidity')
        self.min_target_volume = kwargs.get('min_target_volume')
        self.max_target_volume = kwargs.get('max_target_volume')
        self.min_pool_apy = kwargs.get('min_pool_apy')
        self.max_pool_apy = kwargs.get('max_pool_apy')
        self.min_vault_age = kwargs.get('min_vault_age')
        self.max_vault_age = kwargs.get('max_vault_age')
        self.min_vault_apy = kwargs.get('min_vault_apy')
        self.max_vault_apy = kwargs.get('max_vault_apy')
        self.base_asset_price = kwargs.get('base_asset_price')
        self.precision = kwargs.get('precision')
        self.pricing_model_name = str(kwargs.get('pricing_model_name'))
        self.trade_direction = kwargs.get('trade_direction')
        self.pool_duration = kwargs.get('pool_duration')
        self.num_trading_days = kwargs.get('num_trading_days')
        self.rng = kwargs.get('rng')
        self.verbose = kwargs.get('verbose')
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
            'run_number',
            'model_name',
            'time_until_end',
            'days_until_end',
            'init_time_stretch',
            'target_liquidity',
            'target_daily_volume',
            'pool_apy',
            'fee_percent',
            'floor_fee',
            'init_vault_age',
            'base_asset_price',
            'vault_apy',
            'base_asset_reserves',
            'token_asset_reserves',
            'total_supply',
            'token_in',
            'token_out',
            'trade_direction',
            'trade_amount',
            'trade_amount_usd',
            'share_price', # c in YieldSpace with Yield Bearing Vaults
            'init_share_price', # u in YieldSpace with Yield Bearing Vaults
            'out_without_fee_slippage',
            'out_with_fee',
            'out_without_fee',
            'fee',
            'slippage',
            'pool_duration',
            'num_trading_days',
            'day',
            'run_trade_number',
            'spot_price',
            'num_orders',
            'step_size',
        ]
        self.analysis_dict = {key:[] for key in analysis_keys}

    def set_random_variables(self):
        """Use random number generator to assign initial simulation parameter values"""
        self.target_liquidity = self.rng.uniform(self.min_target_liquidity, self.max_target_liquidity)
        self.target_daily_volume = self.rng.uniform(self.min_target_volume, self.max_target_volume)
        self.init_pool_apy = self.rng.uniform(self.min_pool_apy, self.max_pool_apy) # starting fixed apr
        self.fee_percent = self.rng.uniform(self.min_fee, self.max_fee)
        # Determine real-world parameters for estimating initial (u) and current (c) price-per-share
        self.init_vault_age = self.rng.uniform(self.min_vault_age, self.max_vault_age) # in years
        self.vault_apy = self.rng.uniform(self.min_vault_apy, self.max_vault_apy, size=self.num_trading_days)
        self.vault_apy /= 100 # as a decimal
        self.random_variables_set = True

    def print_random_variables(self):
        """Prints all variables that are set in set_random_variables()"""
        print('Simulation random variables:\n'
            + f'target_liquidity: {self.target_liquidity}\n'
            + f'target_daily_volume: {self.target_daily_volume}\n'
            + f'init_pool_apy: {self.init_pool_apy}\n'
            + f'fee_percent: {self.fee_percent}\n'
            + f'init_vault_age: {self.init_vault_age}\n'
            + f'init_vault_apy: {self.vault_apy[0]}\n' # first element in vault_apy array
        )

    def reset_rng(self, rng):
        """
        Assign the internal random number generator to a new instantiation

        This function is useful for forcing identical trade volume and directions across simulation runs
        """

        assert isinstance(rng, type(np.random.default_rng())), (
            f'rng type must be a random number generator, not {type(rng)}.')
        self.rng = rng

    def setup_pricing_and_market(self, override_dict=None):
        """Constructs the pricing model and market member variables"""
        # Update parameters if the user provided new ones
        assert self.random_variables_set, (
            'ERROR: You must run simulator.set_random_variables() before running the simulation')
        if override_dict is not None:
            for key in override_dict.keys():
                if hasattr(self, key):
                    setattr(self, key, override_dict[key])
                    if key == 'vault_apy':
                        if isinstance(override_dict[key], list):
                            assert len(override_dict[key]) == self.num_trading_days, (
                                f'vault_apy must have len equal to num_trading_days = {self.num_trading_days},'
                                +f' not {len(override_dict[key])}')
                        else:
                            setattr(self, key, [override_dict[key],]*self.num_trading_days)
        if override_dict is not None and 'init_share_price' in override_dict.keys(): # \mu variable
            self.init_share_price = override_dict['init_share_price']
        else:
            init_vault_apy_decimal = self.vault_apy[0] / 100
            self.init_share_price = (1 + init_vault_apy_decimal)**self.init_vault_age
            if self.precision is not None:
                self.init_share_price = np.around(self.init_share_price, self.precision)
        # Initiate pricing model
        if self.pricing_model_name.lower() == 'yieldspacev2':
            self.pricing_model = YieldSpacev2PricingModel(self.verbose, self.floor_fee)
        elif self.pricing_model_name.lower() == 'element':
            self.pricing_model = ElementPricingModel(self.verbose)
        else:
            raise ValueError(f'pricing_model_name must be "YieldSpacev2" or "Element", not {self.pricing_model_name}')
        self.init_time_stretch = self.pricing_model.calc_time_stretch(self.init_pool_apy) # determine time stretch
        (init_base_asset_reserves, init_token_asset_reserves) = self.pricing_model.calc_liquidity(
            self.target_liquidity,
            self.base_asset_price,
            self.init_pool_apy,
            self.pool_duration,
            self.init_time_stretch,
            self.init_share_price, # u from YieldSpace w/ Yield Baring Vaults
            self.init_share_price)[:2] # c from YieldSpace w/ Yield Baring Vaults
        init_days_remaining = self.pricing_model.norm_days(self.pool_duration)
        init_time_remaining = self.pricing_model.stretch_time(init_days_remaining, self.init_time_stretch)
        self.market = Market(
            base_asset=init_base_asset_reserves, # x
            token_asset=init_token_asset_reserves, # y
            fee_percent=self.fee_percent, # g
            time_remaining=init_time_remaining, # t
            pricing_model=self.pricing_model,
            init_share_price=self.init_share_price, # u from YieldSpace w/ Yield Baring Vaults
            share_price=self.init_share_price, # c from YieldSpace w/ Yield Baring Vaults
            verbose=self.verbose)
        # self.step_size = step_scale / (365 * self.init_time_stretch)
        #                = step_scale * (init_time_remaining / self.pool_duration)
        step_scale = 1 # TODO: support scaling the step_size via the override dict (i.e. make a step_scale parameter)
        self.step_size = self.pricing_model.stretch_time(
            self.pricing_model.norm_days(step_scale), self.init_time_stretch)

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
        self.update_analysis_dict() # Initial conditions
        for day in range(0, self.num_trading_days):
            self.day = day
            # APY can vary per day, which sets the current price per share.
            # div by 100 to convert percent to decimal;
            # div by 365 to convert annual to daily;
            # market.init_share_price is the value of 1 share
            self.market.share_price += self.vault_apy[self.day] / 100 / 365 * self.market.init_share_price
            # Loop over trades on the given day
            # TODO: adjustable target daily volume that is a function of the day
            # TODO: improve trading dist, simplify  market price conversion, allow for different amounts
            # Could define a 'trade amount & direction' time series that's a function of the vault apy
            # Could support using actual historical trades or a fit to historical trades)
            day_trading_volume = 0
            while day_trading_volume < self.target_daily_volume:
                # Compute tokens to swap
                token_index = self.rng.integers(low=0, high=2) # 0 or 1
                self.token_in = self.tokens[token_index]
                self.token_out = self.tokens[1-token_index]
                if self.trade_direction == 'in':
                    if self.token_in == 'fyt':
                        target_reserves = self.market.token_asset
                    else:
                        target_reserves = self.market.base_asset
                elif self.trade_direction == 'out':
                    if self.token_in == 'fyt':
                        target_reserves = self.market.base_asset
                    else:
                        target_reserves = self.market.token_asset
                # Compute trade amount, which can't be more than the available reserves.
                trade_mean = self.target_daily_volume / 10
                trade_std = self.target_daily_volume / 100
                self.trade_amount_usd = self.rng.normal(trade_mean, trade_std)
                self.trade_amount_usd = np.minimum(self.trade_amount_usd, target_reserves * self.base_asset_price)
                self.trade_amount = self.trade_amount_usd / self.base_asset_price # convert to token units
                if self.verbose:
                    print(f'trades={self.market.base_asset_orders + self.market.token_asset_orders} '
                        +f'init_share_price={self.market.init_share_price}, '
                        +f'share_price={self.market.share_price}, '
                        +f'amount={self.trade_amount}, '
                        +f'reserves={(self.market.base_asset, self.market.token_asset)}')
                # Conduct trade & update state
                (self.without_fee_or_slippage, self.with_fee, self.without_fee, self.fee) = self.market.swap(
                    self.trade_amount, # in units of target asset
                    self.trade_direction, # out or in
                    self.token_in, # base or fyt
                    self.token_out, # opposite of token_in
                )
                self.update_analysis_dict()
                day_trading_volume += self.trade_amount * self.base_asset_price # track daily volume in USD terms
                self.run_trade_number += 1
            if self.day < self.num_trading_days - 1: # no need to tick the market after the last day
                self.market.tick(self.step_size)
        self.run_number += 1

    def get_days_remaining(self):
        """Returns the days remaining in the pool"""
        time_remaining = self.market.time_remaining
        unstretched_time_remaining = self.pricing_model.unstretch_time(time_remaining, self.init_time_stretch)
        days_remaining = self.pricing_model.unnorm_days(unstretched_time_remaining)
        return days_remaining

    #TODO: Test that this gets the same output as above
    #def calc_days_remaining(self, pool_duration, current_day):
    #    """Calculate the normalized position within the current pool duration"""
    #    return pool_duration - current_day + 1


    def update_analysis_dict(self):
        """Increment the list for each key in the analysis_dict output variable"""
        # Variables that are constant across runs
        self.analysis_dict['model_name'].append(self.market.pricing_model.model_name())
        self.analysis_dict['run_number'].append(self.run_number)
        self.analysis_dict['time_until_end'].append(self.market.time_remaining)
        self.analysis_dict['init_time_stretch'].append(self.init_time_stretch)
        self.analysis_dict['target_liquidity'].append(self.target_liquidity)
        self.analysis_dict['target_daily_volume'].append(self.target_daily_volume)
        self.analysis_dict['fee_percent'].append(self.market.fee_percent)
        self.analysis_dict['floor_fee'].append(self.floor_fee)
        self.analysis_dict['init_vault_age'].append(self.init_vault_age)
        self.analysis_dict['pool_duration'].append(self.pool_duration)
        self.analysis_dict['num_trading_days'].append(self.num_trading_days)
        self.analysis_dict['step_size'].append(self.step_size)
        self.analysis_dict['init_share_price'].append(self.market.init_share_price)
        # Variables that change per run
        self.analysis_dict['day'].append(self.day)
        self.analysis_dict['num_orders'].append(self.market.base_asset_orders + self.market.token_asset_orders)
        self.analysis_dict['vault_apy'].append(self.vault_apy[self.day])
        days_remaining = self.get_days_remaining()
        self.analysis_dict['days_until_end'].append(days_remaining)
        self.analysis_dict['pool_apy'].append(self.market.apy(days_remaining))
        # Variables that change per trade
        self.analysis_dict['run_trade_number'].append(self.run_trade_number)
        self.analysis_dict['base_asset_reserves'].append(self.market.base_asset)
        self.analysis_dict['token_asset_reserves'].append(self.market.token_asset)
        self.analysis_dict['total_supply'].append(self.market.total_supply)
        self.analysis_dict['base_asset_price'].append(self.base_asset_price)
        self.analysis_dict['token_in'].append(self.token_in)
        self.analysis_dict['token_out'].append(self.token_out)
        self.analysis_dict['trade_direction'].append(self.trade_direction)
        self.analysis_dict['trade_amount'].append(self.trade_amount)
        self.analysis_dict['trade_amount_usd'].append(self.trade_amount_usd)
        self.analysis_dict['share_price'].append(self.market.share_price)
        if self.fee is None:
            self.analysis_dict['out_without_fee_slippage'].append(None)
            self.analysis_dict['out_with_fee'].append(None)
            self.analysis_dict['out_without_fee'].append(None)
            self.analysis_dict['fee'].append(None)
            self.analysis_dict['slippage'].append(None)
        else:
            self.analysis_dict['out_without_fee_slippage'].append(self.without_fee_or_slippage * self.base_asset_price)
            self.analysis_dict['out_with_fee'].append(self.with_fee * self.base_asset_price)
            self.analysis_dict['out_without_fee'].append(self.without_fee * self.base_asset_price)
            self.analysis_dict['fee'].append(self.fee * self.base_asset_price)
            slippage = (self.without_fee_or_slippage - self.without_fee) * self.base_asset_price
            self.analysis_dict['slippage'].append(slippage)
        self.analysis_dict['spot_price'].append(self.market.spot_price())


class Market():
    """
    Holds state variables for market simulation and executes trades.

    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(self, base_asset, token_asset, fee_percent, time_remaining,
            pricing_model, init_share_price=1, share_price=1, verbose=False):
        self.base_asset = base_asset # x
        self.token_asset = token_asset # y
        self.fee_percent = fee_percent # g
        self.time_remaining = time_remaining # t
        self.share_price = share_price # c
        self.init_share_price = init_share_price # u normalizing constant
        self.pricing_model = pricing_model
        self.base_asset_orders = 0
        self.token_asset_orders = 0
        self.base_asset_volume = 0
        self.token_asset_volume = 0
        self.cum_token_asset_slippage = 0
        self.cum_base_asset_slippage = 0
        self.cum_token_asset_fees = 0
        self.cum_base_asset_fees = 0
        self.total_supply = self.base_asset + self.token_asset
        self.verbose = verbose

    def apy(self, days_remaining):
        """Returns current APY given the market conditions and pricing model"""
        price = self.pricing_model.calc_spot_price(self.base_asset, self.token_asset,
            self.total_supply, self.time_remaining, self.init_share_price, self.share_price)
        return self.pricing_model.apy(price, days_remaining)

    def spot_price(self):
        """Returns the current spot price given the market conditions and pricing model"""
        return self.pricing_model.calc_spot_price(self.base_asset, self.token_asset,
            self.total_supply, self.time_remaining, self.init_share_price, self.share_price)

    def tick(self, step_size):
        """
        Decrements the time variable by the provided step_size.

        Arguments:
        step_size [float] must be less than self.time_remaining

        It is assumed that self.time_remaining starts at 1 and decreases to 0.
        This function cannot reduce self.time_remaining below 0.
        """

        self.time_remaining -= step_size
        if self.time_remaining < 0:
            assert False, (
                f'ERROR: the time variable market.time_remaining={self.time_remaining} should never be negative.'
                +f'\npricing_model={self.pricing_model}'
            )

    def check_fees(self, amount, direction, token_in, token_out, in_reserves, out_reserves, trade_results):
        """Checks fee values for out of bounds and prints verbose outputs"""
        (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = trade_results
        if self.verbose and self.base_asset_orders + self.token_asset_orders < 10:
            print('total orders are less than 10.')
            print(f'amount={amount}, token_asset+total_supply={self.token_asset + self.total_supply}, '
                +f'base_asset/share_price={self.base_asset / self.share_price}, token_in={token_in}, '
                +f'fee_percent={self.fee_percent}, time_remaining={self.time_remaining}, '
                +f'init_share_price={self.init_share_price}, share_price={self.share_price}')
            print(f'without_fee_or_slippage={without_fee_or_slippage}, '
                +f'output_with_fee={output_with_fee}, output_without_fee={output_without_fee}, fee={fee}')
        if self.verbose and any([
                isinstance(output_with_fee, complex),
                isinstance(output_without_fee, complex),
                isinstance(fee, complex)]):
            max_trade = self.pricing_model.calc_max_trade(in_reserves, out_reserves, self.time_remaining)
            print(f'token_asset+total_supply={self.token_asset + self.total_supply}, '
                +f'base_asset/share_price={self.base_asset / self.share_price}, fee_percent={self.fee_percent}, '
                +f'time_remaining={self.time_remaining}, init_share_price={self.init_share_price}, '
                +f'share_price={self.share_price}')
            print(f'without_fee_or_slippage={without_fee_or_slippage}, '
                +f'output_with_fee={output_with_fee}, output_without_fee={output_without_fee}, fee={fee}')
            assert False, (
                f'Error: fee={fee} type should not be complex.'
                +f'\npricing_modle={self.pricing_model}; direction={direction}; token_in={token_in};'
                +f'token_out={token_out}\nmax_trade={max_trade}; trade_amount={amount};'
                +f'in_reserves={in_reserves}; out_reserves={out_reserves}'
                +f'\ninitial_share_price={self.init_share_price}; share_price={self.share_price}; '
                +f'time_remaining={self.time_remaining}')
        if fee < 0:
            max_trade = self.pricing_model.calc_max_trade(in_reserves, out_reserves, self.time_remaining)
            assert False, (
                f'Error: fee={fee} should never be negative.'
                +f'\npricing_modle={self.pricing_model}; direction={direction}; token_in={token_in};'
                +f'token_out={token_out}\nmax_trade={max_trade}; trade_amount={amount};'
                +f'in_reserves={in_reserves}; out_reserves={out_reserves}'
                +f'\ninitial_share_price={self.init_share_price}; share_price={self.share_price}; '
                +f'time_remaining={self.time_remaining}')

    def update_market(self, d_asset, d_slippage, d_fees, d_orders, d_volume):
        """
        Increments member variables to reflect current market conditions

        All arguments are tuples containing the (base, token) adjustments for each metric
        """
        self.base_asset += d_asset[0]
        self.token_asset += d_asset[1]
        self.cum_base_asset_slippage += d_slippage[0]
        self.cum_token_asset_slippage += d_slippage[1]
        self.cum_base_asset_fees += d_fees[0]
        self.cum_token_asset_fees += d_fees[1]
        self.base_asset_orders += d_orders[0]
        self.token_asset_orders += d_orders[1]
        self.base_asset_volume += d_volume[0]
        self.token_asset_volume += d_volume[1]

    def swap(self, amount, direction, token_in, token_out):
        """
        Execute a trade in the simulated market.

        Arguments:
        amount [float] volume to be traded, in units of the target asset
        direction [str] either "in" or "out"
        token_in [str] either "fyt" or "base" -- must be the opposite of token_out
        token_out [str] either "fyt" or "base" -- must be the opposite of token_in

        Fees are computed, as well as the adjustments in asset volume.
        All internal market variables are updated from the trade.

        TODO: Simplify the logic by forcing token_out to always equal the opposite of token_in
        """

        if direction == "in":
            if token_in == "fyt" and token_out == "base":
                in_reserves = self.token_asset + self.total_supply
                out_reserves = self.base_asset
                trade_results = self.pricing_model.calc_in_given_out(
                    amount, in_reserves, out_reserves, token_in, self.fee_percent,
                    self.time_remaining, self.init_share_price, self.share_price)
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = trade_results
                d_base_asset = -output_with_fee
                d_token_asset = amount
                d_base_asset_slippage = abs(without_fee_or_slippage - output_without_fee)
                d_token_asset_slippage = 0
                d_base_asset_fee = 0
                d_token_asset_fee = fee
                d_base_asset_orders = 1
                d_token_asset_orders = 0
                d_base_asset_volume = output_with_fee
                d_token_asset_volume = 0
            elif token_in == "base" and token_out == "fyt":
                in_reserves = self.base_asset
                out_reserves = self.token_asset + self.total_supply
                trade_results = self.pricing_model.calc_in_given_out(
                    amount, in_reserves, out_reserves, token_in, self.fee_percent,
                    self.time_remaining, self.init_share_price, self.share_price)
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = trade_results
                d_base_asset = amount
                d_token_asset = -output_with_fee
                d_base_asset_slippage = 0
                d_token_asset_slippage = abs(without_fee_or_slippage - output_without_fee)
                d_base_asset_fee = fee
                d_token_asset_fee = 0
                d_base_asset_orders = 0
                d_token_asset_orders = 1
                d_base_asset_volume = 0
                d_token_asset_volume = output_with_fee
            else:
                raise ValueError(
                        'token_in and token_out must be unique and in the set ("base", "fyt"), '
                        +f'not in={token_in} and out={token_out}')
        elif direction == "out":
            if token_in == "fyt" and token_out == "base":
                in_reserves = self.token_asset + self.total_supply
                out_reserves = self.base_asset
                trade_results = self.pricing_model.calc_out_given_in(
                    amount, in_reserves, out_reserves, token_out, self.fee_percent,
                    self.time_remaining, self.init_share_price, self.share_price)
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = trade_results
                d_base_asset = -output_with_fee
                d_token_asset = amount
                d_base_asset_slippage = abs(without_fee_or_slippage - output_without_fee)
                d_token_asset_slippage = 0
                d_base_asset_fee = fee
                d_token_asset_fee = 0
                d_base_asset_orders = 1
                d_token_asset_orders = 0
                d_base_asset_volume = output_with_fee
                d_token_asset_volume = 0
            elif token_in == "base" and token_out == "fyt":
                in_reserves = self.base_asset
                out_reserves = self.token_asset + self.total_supply
                trade_results = self.pricing_model.calc_out_given_in(
                    amount, in_reserves, out_reserves, token_out, self.fee_percent,
                    self.time_remaining, self.init_share_price, self.share_price)
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = trade_results
                d_base_asset = amount
                d_token_asset = -output_with_fee
                d_base_asset_slippage = 0
                d_token_asset_slippage = abs(without_fee_or_slippage - output_without_fee)
                d_base_asset_fee = 0
                d_token_asset_fee = fee
                d_base_asset_orders = 0
                d_token_asset_orders = 1
                d_base_asset_volume = 0
                d_token_asset_volume = output_with_fee
        else:
            raise ValueError(f'direction argument must be "in" or "out", not {direction}')
        self.check_fees(amount, direction, token_in, token_out, in_reserves, out_reserves, trade_results)
        self.update_market(
            (d_base_asset, d_token_asset),
            (d_base_asset_slippage, d_token_asset_slippage),
            (d_base_asset_fee, d_token_asset_fee),
            (d_base_asset_orders, d_token_asset_orders),
            (d_base_asset_volume, d_token_asset_volume)
        )
        return (without_fee_or_slippage, output_with_fee, output_without_fee, fee)



class PricingModel(object):
    """
    Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class

    TODO: Change argument defaults to be None & set inside of def to avoid accidental overwrite
    """

    def __init__(self, verbose=None):
        self.verbose = False if verbose is None else verbose

    def calc_in_given_out(self, out, in_reserves, out_reserves, token_in,
            fee_percent, time_remaining, init_share_price, share_price):
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_out_given_in(self, in_, in_reserves, out_reserves, token_out,
            fee_percent, time_remaining, init_share_price, share_price):
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def model_name(self):
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

    @staticmethod
    def norm_days(days, normalizing_constant=365):
        """Returns days normalized between 0 and 1, with a default assumption of a year-long scale"""
        return days / normalizing_constant

    @staticmethod
    def stretch_time(time, time_stretch=1):
        """Returns stretched time values"""
        return time / time_stretch

    @staticmethod
    def unnorm_days(normed_days, normalizing_constant=365):
        """Returns days from a value between 0 and 1"""
        return normed_days * normalizing_constant

    @staticmethod
    def unstretch_time(stretched_time, time_stretch=1):
        """Returns unstretched time value, which should be between 0 and 1"""
        return stretched_time * time_stretch

    @staticmethod
    def calc_time_stretch(apy):
        """Returns fixed time-stretch value based on current apy"""
        return 3.09396 / (0.02789 * apy)

    @staticmethod
    def calc_tokens_in_given_lp_out(lp_out, base_asset_reserves, token_asset_reserves, total_supply):
        """Returns how much supply is needed if liquidity is removed"""
        # Check if the pool is initialized
        if total_supply == 0:
            base_asset_needed = lp_out
            token_asset_needed = 0
        else:
            # solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply) / x_reserves
            token_asset_needed = (
                (lp_out * base_asset_reserves)
                /
                ((base_asset_reserves / token_asset_reserves) * total_supply)
            )
            # solve for x_needed: x_reserves / y_reserves = x_needed / y_needed
            base_asset_needed = (base_asset_reserves / token_asset_reserves) * token_asset_needed
        return (base_asset_needed, token_asset_needed)

    @staticmethod
    def calc_lp_out_given_tokens_in(base_asset_in, token_asset_in, base_asset_reserves,
            token_asset_reserves, total_supply):
        """Returns how much liquidity can be removed given newly minted assets"""
        # Check if the pool is initialized
        if total_supply == 0:
            # When uninitialized we mint exactly the underlying input in LP tokens
            lp_out = base_asset_in
            base_asset_needed = base_asset_in
            token_asset_needed = 0
        else:
            # Calc the number of base_asset needed for the y_in provided
            base_asset_needed = (base_asset_reserves / token_asset_reserves) * token_asset_in
            # If there isn't enough x_in provided
            if base_asset_needed > base_asset_in:
                lp_out = (base_asset_in * total_supply) / base_asset_reserves
                base_asset_needed = base_asset_in # use all the x_in
                # Solve for: x_reserves / y_reserves = x_needed / y_needed
                token_asset_needed = base_asset_needed / (base_asset_reserves / token_asset_reserves)
            else:
                # We calculate the percent increase in the reserves from contributing all of the bond
                lp_out = (base_asset_needed * total_supply) / base_asset_reserves
                token_asset_needed = token_asset_in
        return (base_asset_needed, token_asset_needed, lp_out)

    @staticmethod
    def calc_lp_in_given_tokens_out(min_base_asset_out, min_token_asset_out, base_asset_reserves,
            token_asset_reserves, total_supply):
        """Returns how much liquidity is needed given a removal of asset quantities"""
        # Calc the number of base_asset needed for the y_out provided
        base_asset_needed = (base_asset_reserves / token_asset_reserves) * min_token_asset_out
        # If there isn't enough x_out provided
        if min_base_asset_out > base_asset_needed:
            lp_in = (min_base_asset_out * total_supply) / base_asset_reserves
            base_asset_needed = min_base_asset_out # use all the x_out
            # Solve for: x_reserves/y_reserves = x_needed/y_needed
            token_asset_needed = base_asset_needed / (base_asset_reserves / token_asset_reserves)
        else:
            token_asset_needed = min_token_asset_out
            lp_in = (token_asset_needed * total_supply) / token_asset_reserves
        return (base_asset_needed, token_asset_needed, lp_in)

    @staticmethod
    def calc_tokens_out_for_lp_in(lp_in, base_asset_reserves, token_asset_reserves, total_supply):
        """Returns allowable asset reduction for an increase in liquidity"""
        # Solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply)/x_reserves
        token_asset_needed = (
            (lp_in * base_asset_reserves)
            /
            ((base_asset_reserves / token_asset_reserves) * total_supply)
        )
        # Solve for x_needed: x_reserves/y_reserves = x_needed/y_needed
        base_asset_needed = (base_asset_reserves / token_asset_reserves) * token_asset_needed
        return (base_asset_needed, token_asset_needed)

    @staticmethod
    def calc_k_const(in_reserves, out_reserves, time_elapsed, scale=1):
        """Returns the 'k' constant variable for trade mathematics"""
        return scale * in_reserves**(time_elapsed) + out_reserves**(time_elapsed)

    def calc_max_trade(self, in_reserves, out_reserves, time_remaining):
        """Returns the maximum allowable trade amount given the current asset reserves"""
        time_elapsed = 1 - time_remaining
        k = self.calc_k_const(in_reserves, out_reserves, time_elapsed)#in_reserves**(1 - t) + out_reserves**(1 - t)
        return k**(1 / time_elapsed) - in_reserves

    def apy(self, price, days_remaining):
        """Returns the APY given the current (positive) base asset price and the remaining pool duration"""
        assert price > 0, (
            f'price argument should be greater than zero, not {price}')
        assert days_remaining > 0, (
            f'days_remaining argument should be greater than zero, not {days_remaining}')
        normalized_days_remaining = self.norm_days(days_remaining)
        return (1 - price) / price / normalized_days_remaining * 100 # APYW

    # TODO: Test that the following two functions return the same amount
    def calc_spot_price(self, base_asset_reserves, token_asset_reserves,
            total_supply, time_remaining, init_share_price=1, share_price=1):
        """Returns the spot price given the current supply and temporal position along the yield curve"""
        inv_log_price = share_price * (token_asset_reserves + total_supply) / (init_share_price * base_asset_reserves)
        spot_price = 1 / inv_log_price**time_remaining
        return spot_price

    def calc_spot_price_from_apy(self, apy, days_remaining):
        """Returns the current spot price based on the current APY and the remaining pool duration"""
        normalized_days_remaining = self.norm_days(days_remaining)
        apy_decimal = apy / 100
        return 1 - apy_decimal * normalized_days_remaining

    def calc_apy_from_reserves(self, base_asset_reserves, token_asset_reserves, total_supply,
            time_remaining, time_stretch, init_share_price=1, share_price=1):
        """Returns the apy given reserve amounts"""
        spot_price = self.calc_spot_price(
            base_asset_reserves, token_asset_reserves, total_supply, time_remaining, init_share_price, share_price)
        days_remaining = self.unnorm_days(self.unstretch_time(time_remaining, time_stretch))
        return self.apy(spot_price, days_remaining)

    def calc_base_asset_reserves(self, apy, token_asset_reserves, days_remaining, time_stretch,
            init_share_price, share_price):
        """Returns the assumed base_asset reserve amounts given the token_asset reserves and APY"""
        normalized_days_remaining = self.norm_days(days_remaining)
        time_stretch_exp = 1 / self.stretch_time(normalized_days_remaining, time_stretch)
        apy_decimal = apy / 100
        numerator = 2 * share_price * token_asset_reserves
        inv_scaled_apy_decimal = 1 / (apy_decimal * normalized_days_remaining - 1)
        denominator = (init_share_price * (-inv_scaled_apy_decimal)**time_stretch_exp - share_price)
        result = numerator / denominator
        if self.verbose:
            print(f'calc_base_asset_reserves result: {result}')
        return result

    def calc_liquidity(self, target_liquidity, market_price, apy,
            days_remaining, time_stretch, init_share_price=1, share_price=1):
        """Returns the reserve volumes and liquidity amounts"""
        spot_price = self.calc_spot_price_from_apy(apy, days_remaining)
        time_remaining = self.stretch_time(self.norm_days(days_remaining), time_stretch)
        token_asset_reserves = target_liquidity / market_price / 2 / (1 - apy / 100 * time_remaining)
        base_asset_reserves = self.calc_base_asset_reserves(
                apy, token_asset_reserves, days_remaining, time_stretch, init_share_price, share_price)
        scale_up_factor = (
            target_liquidity
            /
            (base_asset_reserves * market_price + token_asset_reserves * market_price * spot_price)
        )
        token_asset_reserves = token_asset_reserves * scale_up_factor
        base_asset_reserves = base_asset_reserves * scale_up_factor
        liquidity = base_asset_reserves * market_price + token_asset_reserves * market_price * spot_price
        if self.verbose:
            total_supply = base_asset_reserves + token_asset_reserves
            actual_apy = self.calc_apy_from_reserves(
                base_asset_reserves, token_asset_reserves, total_supply, time_remaining,
                time_stretch, init_share_price, share_price)
            print(f'base_asset_reserves={base_asset_reserves}, token_asset={token_asset_reserves}, '
                +f'total={liquidity}, apy={actual_apy}')
        return (base_asset_reserves, token_asset_reserves, liquidity)


class ElementPricingModel(PricingModel):
    """
    Element v1 pricing model

    Does not use the Yield Bearing Vault `init_share_price` (u) and `share_price` (c) variables.
    """

    def model_name(self):
        return "Element"

    def calc_in_given_out(self, out, in_reserves, out_reserves, token_in, fee_percent,
            time_remaining, init_share_price=1, share_price=1):
        time_elapsed = 1 - time_remaining
        k = self.calc_k_const(in_reserves, out_reserves, time_elapsed) # in_reserves**(1 - t) + out_reserves**(1 - t)
        without_fee = (k - (out_reserves - out)**time_elapsed)**(1 / time_elapsed) - in_reserves
        if token_in == "base":
            fee = fee_percent * (out - without_fee)
        elif token_in == "fyt":
            fee = fee_percent * (without_fee - out)
        with_fee = without_fee + fee
        without_fee_or_slippage = out * (in_reserves / out_reserves)**time_remaining
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_out_given_in(self, in_, in_reserves, out_reserves, token_out, fee_percent,
            time_remaining, init_share_price=1, share_price=1):
        time_elapsed = 1 - time_remaining
        k = self.calc_k_const(in_reserves, out_reserves, time_elapsed) # in_reserves**(1 - t) + out_reserves**(1 - t)
        without_fee = out_reserves - pow(k - pow(in_reserves + in_, time_elapsed), 1 / time_elapsed)
        if token_out == "base":
            fee = fee_percent * (in_ - without_fee)
        elif token_out == "fyt":
            fee = fee_percent * (without_fee - in_)
        with_fee = without_fee - fee
        without_fee_or_slippage = in_ / (in_reserves / out_reserves)**time_remaining
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_base_asset_reserves(self, apy, token_asset_reserves, days_remaining,
            time_stretch, init_share_price=1, share_price=1):
        return super().calc_base_asset_reserves(
            apy, token_asset_reserves, days_remaining, time_stretch, init_share_price, share_price)


class YieldSpacev2PricingModel(PricingModel):
    """
    V2 pricing model that uses Yield Bearing Vault equations
    """

    def __init__(self, verbose=False, floor_fee=0):
        super().__init__(verbose)
        self.floor_fee = floor_fee

    def model_name(self):
        if self.floor_fee > 0:
            return "YieldSpacev2MinFee"
        return "YieldSpacev2"

    def calc_in_given_out(self, out, in_reserves, out_reserves, token_in, fee_percent,
            time_remaining, init_share_price, share_price):
        scale = share_price / init_share_price
        time_elapsed = 1 - time_remaining
        if token_in == "base": # calc shares in for fyt out
            d_token_asset = out
            share_reserves = in_reserves / share_price # convert from base_asset to z (x=cz)
            token_asset = out_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self.calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            inv_init_share_price = 1 / init_share_price
            new_token_asset = token_asset - d_token_asset
            without_fee = (
                inv_init_share_price * ((k - new_token_asset**time_elapsed) / scale)**(1 / time_elapsed)
                - share_reserves
            ) * share_price
            # Fee math
            fee = (out - without_fee) * fee_percent
            with_fee = without_fee + fee
            without_fee_or_slippage = (
                out * (in_reserves / (share_price / init_share_price * out_reserves))**time_remaining)
        elif token_in == "fyt": # calc fyt in for shares out
            d_share_reserves = out / share_price
            share_reserves = out_reserves / share_price # convert from base_asset to z (x=cz)
            token_asset = in_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self.calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            without_fee = (
                k - scale
                * (init_share_price * share_reserves - init_share_price * d_share_reserves)**time_elapsed
            )**(1 / time_elapsed) - token_asset
            # Fee math
            fee = (without_fee - out) * fee_percent
            with_fee = without_fee + fee
            without_fee_or_slippage = (
                out * ((share_price / init_share_price * in_reserves) / out_reserves)**time_remaining)
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_out_given_in(self, in_, in_reserves, out_reserves, token_out, fee_percent,
            time_remaining, init_share_price, share_price):
        scale = share_price / init_share_price # normalized function of vault yields
        time_elapsed = 1 - time_remaining
        if token_out == "base": # calc shares out for fyt in
            d_token_asset = in_
            share_reserves = out_reserves / share_price # convert from x to z (x=cz)
            token_asset = in_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self.calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            inv_init_share_price = 1 / init_share_price
            without_fee = (
                share_reserves - inv_init_share_price
                * ((k - (token_asset + d_token_asset)**time_elapsed) / scale)**(1 / time_elapsed)
            ) * share_price
            # Fee math
            fee = (in_ - without_fee) * fee_percent
            assert fee >= 0, ('ERROR: Fee should not be negative')
            if fee / in_ < self.floor_fee / 100 / 100:
                fee = in_ * self.floor_fee / 100 / 100
            with_fee = without_fee - fee
            without_fee_or_slippage = (
                1 / ((share_price / init_share_price * in_reserves) / out_reserves)**time_remaining * in_)
        elif token_out == "fyt": # calc fyt out for shares in
            d_share_reserves = in_ / share_price # convert from base_asset to z (x=cz)
            share_reserves = in_reserves / share_price # convert from base_asset to z (x=cz)
            token_asset = out_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self.calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            without_fee = token_asset - (
                k - scale * (init_share_price * share_reserves + init_share_price * d_share_reserves)**time_elapsed
            )**(1 / time_elapsed)
            # Fee math
            fee = (without_fee - in_) * fee_percent
            assert fee >= 0, ('ERROR: Fee should not be negative')
            if fee / in_ < self.floor_fee / 100 / 100:
                fee = in_ * self.floor_fee / 100 / 100
            with_fee = without_fee - fee
            without_fee_or_slippage = (
                1 / (in_reserves / (share_price / init_share_price * out_reserves))**time_remaining * in_
            )
        return (without_fee_or_slippage, with_fee, without_fee, fee)
