import numpy as np

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals

class YieldSimulator():
    """
    Stores environment varialbes & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes

    # TODO: completely remove calc_in_given_out
    # TODO: Move away from using kwargs (this was a hack and can introduce bugs if the dict gets updated)
    # Better to do named & typed args w/ defaults
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
        self.days_until_maturity = kwargs.get('days_until_maturity')
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
        self.init_price_per_share = None
        self.t_stretch = None
        self.pricing_model = None
        self.market = None
        self.step_size = None
        self.day = None
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
            't_stretch',
            'target_liquidity',
            'target_daily_volume',
            'pool_apy',
            'fee_percent',
            'floor_fee',
            'init_vault_age',
            'base_asset_price',
            'vault_apy',
            'x_reserves',
            'y_reserves',
            'total_supply',
            'token_in',
            'token_out',
            'trade_direction',
            'trade_amount',
            'trade_amount_usd',
            'price_per_share', # c in YieldSpace with Yield Bearing Vaults
            'init_price_per_share', # u in YieldSpace with Yield Bearing Vaults
            'out_without_fee_slippage',
            'out_with_fee',
            'out_without_fee',
            'fee',
            'slippage',
            'days_until_maturity',
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
        # Determine real-world parameters for estimating u and c (vault and pool details)
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

        assert isinstance(rng, np.random.default_rng()), (
            f'rng type must be a random number generator, not {type(rng)}.')
        self.rng = rng

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
        if override_dict is not None and 'init_price_per_share' in override_dict.keys(): # \mu variable 
            self.init_price_per_share = override_dict['init_price_per_share']
        else:
            self.init_price_per_share = (1 + self.vault_apy[0]/100)**self.init_vault_age
            if self.precision is not None:
                self.init_price_per_share = np.around(self.init_price_per_share, self.precision)
        # Initiate pricing model
        if self.pricing_model_name.lower() == 'yieldspacev2':
            self.pricing_model = YieldSpacev2PricingModel(self.verbose, self.floor_fee)
        elif self.pricing_model_name.lower() == 'element':
            self.pricing_model = ElementPricingModel(self.verbose)
        else:
            raise ValueError(f'pricing_model_name must be "YieldSpacev2" or "Element", not {self.pricing_model_name}')
        self.t_stretch = self.pricing_model.calc_time_stretch(self.init_pool_apy) # determine time stretch

        (init_x_reserves, init_y_reserves) = self.pricing_model.calc_liquidity(
            self.target_liquidity,
            self.base_asset_price,
            self.init_pool_apy,
            self.days_until_maturity,
            self.t_stretch,
            self.init_price_per_share, # u from YieldSpace w/ Yield Baring Vaults
            self.init_price_per_share)[:2] # c from YieldSpace w/ Yield Baring Vaults
        init_total_supply = init_x_reserves + init_y_reserves

        self.market = Market(
            x=init_x_reserves,
            y=init_y_reserves,
            g=self.fee_percent,
            t=self.days_until_maturity / (365 * self.t_stretch), # stored as t inside Market class
            total_supply=init_total_supply,
            pricing_model=self.pricing_model,
            u=self.init_price_per_share, # u from YieldSpace w/ Yield Baring Vaults
            c=self.init_price_per_share, # c from YieldSpace w/ Yield Baring Vaults
            verbose=self.verbose)

        # TODO: Allow one to alternatively specify a step_size in the override dict
        self.step_size = self.market.t / self.days_until_maturity

        self.update_analysis_dict() # Initial conditions
        for day in range(0, self.num_trading_days):
            self.day = day
            # APY can vary per day, which sets the current price per share.
            # div by 100 to convert percent to decimal;
            # div by 365 to convert annual to daily;
            # market.u is the value of 1 share
            self.market.c += self.vault_apy[self.day] / 100 / 365 * self.market.u

            # Loop over trades on the given day
            # TODO: adjustable target daily volume that is a function of the day
            day_trading_volume = 0
            while day_trading_volume < self.target_daily_volume:
                # Compute trade amount (converted from USD to token units)
                self.trade_amount_usd = self.rng.normal(self.target_daily_volume / 10, self.target_daily_volume / 100)
                self.trade_amount_usd = self.target_daily_volume / 10

                # TODO: improve trading distribution & simplify (remove?) market price conversion & allow for different trade amounts
                # Could define a 'trade amount & direction' time series that's a function of the vault apy
                # Could support using actual historical trades or a fit to historical trades)
                # Compute tokens to swap
                token_index = self.rng.integers(low=0, high=2) # 0 or 1
                self.token_in = self.tokens[token_index]
                self.token_out = self.tokens[1-token_index]

                (x_reserves, y_reserves) = (self.market.x, self.market.y) # in token units
                if self.trade_direction == 'in':
                    target_reserves = y_reserves if self.token_in == 'fyt' else x_reserves # Assumes 'in' direction
                elif self.trade_direction == 'out':
                    target_reserves = x_reserves if self.token_in == 'fyt' else y_reserves # Assumes 'out' direction
                # variable is in token units. Can't trade more than available reserves.
                self.trade_amount = np.minimum(self.trade_amount_usd / self.base_asset_price, target_reserves)
                if self.verbose:
                    print(f'trades={self.market.x_orders+self.market.y_orders} (c,u)=({self.market.c}, '
                        +f'{self.market.u})amount={self.trade_amount} reserves={(x_reserves,y_reserves)}')

                # Conduct trade & update state
                (self.without_fee_or_slippage, self.with_fee, self.without_fee, self.fee) = self.market.swap(
                    self.trade_amount, # in units of target asset
                    self.trade_direction,
                    self.token_in,
                    self.token_out)
                self.update_analysis_dict()

                day_trading_volume += self.trade_amount * self.base_asset_price # track daily volume in USD terms
                self.run_trade_number += 1
            if day < self.num_trading_days-1: # no need to tick the market after the last day
                self.market.tick(self.step_size)
        self.run_number += 1

    def update_analysis_dict(self):
        """Increment the list for each key in the analysis_dict output variable"""
        # Variables that are constant across runs
        self.analysis_dict['model_name'].append(self.market.pricing_model.model_name())
        self.analysis_dict['run_number'].append(self.run_number)
        self.analysis_dict['time_until_end'].append(self.market.t)
        self.analysis_dict['t_stretch'].append(self.t_stretch) # TODO: rename to time_stretch
        self.analysis_dict['target_liquidity'].append(self.target_liquidity)
        self.analysis_dict['target_daily_volume'].append(self.target_daily_volume)
        self.analysis_dict['pool_apy'].append(self.market.apy(self.days_until_maturity - self.day + 1))
        self.analysis_dict['fee_percent'].append(self.fee_percent)
        self.analysis_dict['floor_fee'].append(self.floor_fee)
        self.analysis_dict['init_vault_age'].append(self.init_vault_age)
        self.analysis_dict['days_until_maturity'].append(self.days_until_maturity)
        self.analysis_dict['num_trading_days'].append(self.num_trading_days)
        self.analysis_dict['step_size'].append(self.step_size)
        # Variables that change per run
        self.analysis_dict['day'].append(self.day)
        self.analysis_dict['num_orders'].append(self.market.x_orders + self.market.y_orders)
        self.analysis_dict['vault_apy'].append(self.vault_apy[self.day])
        # Variables that change per trade
        self.analysis_dict['run_trade_number'].append(self.run_trade_number)
        self.analysis_dict['x_reserves'].append(self.market.x)
        self.analysis_dict['y_reserves'].append(self.market.y)
        self.analysis_dict['total_supply'].append(self.market.total_supply)
        self.analysis_dict['base_asset_price'].append(self.base_asset_price)
        self.analysis_dict['token_in'].append(self.token_in)
        self.analysis_dict['token_out'].append(self.token_out)
        self.analysis_dict['trade_direction'].append(self.trade_direction)
        self.analysis_dict['trade_amount'].append(self.trade_amount)
        self.analysis_dict['trade_amount_usd'].append(self.trade_amount_usd)
        self.analysis_dict['price_per_share'].append(self.market.c)
        self.analysis_dict['init_price_per_share'].append(self.market.u)
        self.analysis_dict['out_without_fee_slippage'].append(self.without_fee_or_slippage * self.base_asset_price)
        self.analysis_dict['out_with_fee'].append(self.with_fee * self.base_asset_price)
        self.analysis_dict['out_without_fee'].append(self.without_fee * self.base_asset_price)
        self.analysis_dict['fee'].append(self.fee*self.base_asset_price)
        self.analysis_dict['slippage'].append((self.without_fee_or_slippage - self.without_fee) * self.base_asset_price)
        self.analysis_dict['spot_price'].append(self.market.spot_price())


class Market(object):
    """
    Holds state variables for market simulation and executes trades.

    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(self, x, y, g, t, total_supply, pricing_model, u=1, c=1, verbose=False):
        self.x = x
        self.y = y
        self.total_supply = total_supply
        self.g = g
        self.t = t
        self.c = c # conversion rate
        self.u = u # normalizing constant
        self.pricing_model = pricing_model
        self.x_orders = 0
        self.y_orders = 0
        self.x_volume = 0
        self.y_volume = 0
        self.cum_y_slippage = 0
        self.cum_x_slippage = 0
        self.cum_y_fees = 0
        self.cum_x_fees = 0
        self.starting_fyt_price = self.spot_price()
        self.verbose = verbose

    def apy(self, days_until_maturity):
        """Returns current APY given the market conditions and pricing model"""
        price = self.pricing_model.calc_spot_price(self.x, self.y, self.total_supply, self.t, self.u, self.c)
        return self.pricing_model.apy(price, days_until_maturity)

    def spot_price(self):
        """Returns the current spot price given the market conditions and pricing model"""
        return self.pricing_model.calc_spot_price(self.x, self.y, self.total_supply, self.t, self.u, self.c)

    def tick(self, step_size):
        """
        Decrements the time variable by the provided step_size.

        Arguments:
        step_size [float] must be less than self.t 

        It is assumed that self.t starts at 1 and decreases to 0.
        This function cannot reduce self.t below 0.
        """

        self.t -= step_size
        if self.t < 0:
            assert False, (
                f'ERROR: the time variable market.t={self.t} should never be negative.'
                +f'\npricing_model={self.pricing_model}'
            )

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
        """

        if direction == "in":
            if token_in == "fyt" and token_out == "base":
                in_reserves = self.y + self.total_supply
                out_reserves = self.x
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = \
                        self.pricing_model.calc_in_given_out(
                                amount, in_reserves, out_reserves, token_in, self.g, self.t, self.u, self.c)
                dx = -output_with_fee
                dy = amount
                dx_slippage = abs(without_fee_or_slippage - output_without_fee)
                dy_slippage = 0
                dx_fee = 0
                dy_fee = fee
                dx_orders = 1
                dy_orders = 0
                dx_volume = output_with_fee
                dy_volume = 0
            elif token_in == "base" and token_out == "fyt":
                in_reserves = self.x
                out_reserves = self.y + self.total_supply
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = \
                        self.pricing_model.calc_in_given_out(
                                amount, in_reserves, out_reserves, token_in, self.g, self.t, self.u, self.c)
                dx = amount
                dy = -output_with_fee
                dx_slippage = 0
                dy_slippage = abs(without_fee_or_slippage - output_without_fee)
                dx_fee = fee
                dy_fee = 0
                dx_orders = 0
                dy_orders = 1
                dx_volume = 0
                dy_volume = output_with_fee
            else:
                raise ValueError(
                        'token_in and token_out must be unique and in the set ("base", "fyt"), '
                        +f'not in={token_in} and out={token_out}')
        elif direction == "out":
            if token_in == "fyt" and token_out == "base":
                in_reserves = self.y + self.total_supply
                out_reserves = self.x
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = \
                        self.pricing_model.calc_out_given_in(
                                amount, in_reserves, out_reserves, token_out, self.g, self.t, self.u, self.c)
                dx = -output_with_fee
                dy = amount
                dx_slippage = abs(without_fee_or_slippage - output_without_fee)
                dy_slippage = 0
                dx_fee = fee
                dy_fee = 0
                dx_orders = 1
                dy_orders = 0
                dx_volume = output_with_fee
                dy_volume = 0
            elif token_in == "base" and token_out == "fyt":
                in_reserves = self.x
                out_reserves = self.y + self.total_supply
                (without_fee_or_slippage, output_with_fee, output_without_fee, fee) = \
                        self.pricing_model.calc_out_given_in(
                                amount, in_reserves, out_reserves, token_out, self.g, self.t, self.u, self.c)
                dx = amount
                dy = -output_with_fee
                dx_slippage = 0
                dy_slippage = abs(without_fee_or_slippage - output_without_fee)
                dx_fee = 0
                dy_fee = fee
                dx_orders = 0
                dy_orders = 1
                dx_volume = 0
                dy_volume = output_with_fee
        else:
            raise ValueError(f'direction argument must be "in" or "out", not {direction}')
        if self.verbose and self.x_orders + self.y_orders < 10:
            print('conditional one')
            print([amount, self.y + self.total_supply, self.x / self.c, token_in, self.g, self.t, self.u, self.c])
            print([without_fee_or_slippage, output_with_fee, output_without_fee, fee])
        if self.verbose and any([
                isinstance(output_with_fee, complex),
                isinstance(output_without_fee, complex),
                isinstance(fee, complex)]):
            print([amount, self.y + self.total_supply, self.x, token_in, self.g, self.t, self.u, self.c])
            print([(without_fee_or_slippage, output_with_fee, output_without_fee, fee)])
        if isinstance(fee, complex):
            max_trade = self.pricing_model.calc_max_trade(in_reserves, out_reserves, self.t)
            assert False, (
                f'Error: fee={fee} type should not be complex.'
                +f'\npricing_modle={self.pricing_model}; direction={direction}; token_in={token_in};'
                +f'token_out={token_out}\nmax_trade={max_trade}; trade_amount={amount};'
                +f'in_reserves={in_reserves}; out_reserves={out_reserves}'
                +f'\ninitial_price_per_share={self.u}; price_per_share={self.c}; time={self.t}'
            )
        if fee < 0:
            max_trade = self.pricing_model.calc_max_trade(in_reserves, out_reserves, self.t)
            assert False, (
                f'Error: fee={fee} should never be negative.'
                +f'\npricing_modle={self.pricing_model}; direction={direction}; token_in={token_in};'
                +f'token_out={token_out}\nmax_trade={max_trade}; trade_amount={amount};'
                +f'in_reserves={in_reserves}; out_reserves={out_reserves}'
                +f'\ninitial_price_per_share={self.u}; price_per_share={self.c}; time={self.t}'
            )
        # TODO: (dp) prev code did not do these if fee == 0, but I think you should?
        self.x += dx
        self.y += dy
        self.cum_x_slippage += dx_slippage
        self.cum_y_slippage += dy_slippage
        self.cum_x_fees += dx_fee
        self.cum_y_fees += dy_fee
        self.x_orders += dx_orders
        self.y_orders += dy_orders
        self.x_volume += dx_volume
        self.y_volume += dy_volume
        return (without_fee_or_slippage, output_with_fee, output_without_fee, fee)


class PricingModel(object):
    """
    Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class

    # TODO: Change argument defaults to be None & set inside of def to avoid accidental overwrite
    """

    def __init__(self, verbose=None):
        self.verbose = False if verbose is None else verbose

    def calc_in_given_out(self, out, in_reserves, out_reserves, token_in, g, t, u, c):
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_out_given_in(self, in_, in_reserves, out_reserves, token_out, g, t, u, c):
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def model_name(self):
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

    @staticmethod
    def calc_time_stretch(apy):
        """Returns fixed time-stretch value based on current apy"""
        return 3.09396 / (0.02789 * apy)

    @staticmethod
    def calc_tokens_in_given_lp_out(lp_out, x_reserves, y_reserves, total_supply):
        """Returns how much supply is needed if liquidity is removed"""
        # Check if the pool is initialized
        if total_supply == 0:
            x_needed = lp_out
            y_needed = 0
        else:
            # solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply)/x_reserves
            y_needed = (lp_out * x_reserves) / ((x_reserves / y_reserves) * total_supply)
            # solve for x_needed: x_reserves / y_reserves = x_needed / y_needed
            x_needed = (x_reserves / y_reserves) * y_needed
        return (x_needed, y_needed)

    @staticmethod
    def calc_lp_out_given_tokens_in(x_in, y_in, x_reserves, y_reserves, total_supply):
        """Returns how much liquidity can be removed given newly minted assets"""
        # Check if the pool is initialized
        if total_supply == 0:
            # When uninitialized we mint exactly the underlying input in LP tokens
            lp_out = x_in
            x_needed = x_in
            y_needed = 0
        else:
            # Calc the number of x needed for the y_in provided
            x_needed = (x_reserves / y_reserves) * y_in
            # If there isn't enough x_in provided
            if x_needed > x_in:
                lp_out = (x_in * total_supply) / x_reserves
                x_needed = x_in # use all the x_in
                # Solve for: x_reserves/y_reserves = x_needed/y_needed
                y_needed = x_needed / (x_reserves / y_reserves)
            else:
                # We calculate the percent increase in the reserves from contributing all of the bond
                lp_out = (x_needed * total_supply) / x_reserves
                y_needed = y_in
        return (x_needed, y_needed, lp_out)

    @staticmethod
    def calc_lp_in_given_tokens_out(min_x_out, min_y_out, x_reserves, y_reserves, total_supply):
        """Returns how much liquidity is needed given a removal of asset quantities"""
        # Calc the number of x needed for the y_out provided
        x_needed = (x_reserves / y_reserves) * min_y_out
        # If there isn't enough x_out provided
        if min_x_out > x_needed:
            lp_in = (min_x_out * total_supply) / x_reserves
            x_needed = min_x_out # use all the x_out
            # Solve for: x_reserves/y_reserves = x_needed/y_needed
            y_needed = x_needed / (x_reserves / y_reserves)
        else:
            y_needed = min_y_out
            lp_in = (y_needed * total_supply) / y_reserves
        return (x_needed, y_needed, lp_in)

    @staticmethod
    def calc_tokens_out_for_lp_in(lp_in, x_reserves, y_reserves, total_supply):
        """Returns allowable asset reduction for an increase in liquidity"""
        # Solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply)/x_reserves
        y_needed = (lp_in * x_reserves) / ((x_reserves / y_reserves) * total_supply)
        # Solve for x_needed: x_reserves/y_reserves = x_needed/y_needed
        x_needed = (x_reserves / y_reserves) * y_needed
        return (x_needed, y_needed)

    @staticmethod
    def calc_k_const(in_reserves, out_reserves, t, scale=1):
        """Returns the 'k' constant variable for trade mathematics"""
        return scale * in_reserves**(1 - t) + out_reserves**(1 - t)

    def calc_max_trade(self, in_reserves, out_reserves, t):
        """Returns the maximum allowable trade amount given the current asset reserves"""
        k = self.calc_k_const(in_reserves, out_reserves, t)#in_reserves**(1 - t) + out_reserves**(1 - t)
        return k**(1 / (1 - t)) - in_reserves

    def apy(self, price, days_until_maturity):
        """Returns the APY given the current (positive) base asset price and the total pool duration"""
        assert price > 0, (
            f'price argument should be greater than zero, not {price}')
        assert days_until_maturity > 0, (
            f'days_until_maturity argument should be greater than zero, not {days_until_maturity}')
        normalized_pool_duration = days_until_maturity / 365
        return (1 - price) / price / normalized_pool_duration * 100 # APYW

    def calc_spot_price(self, x_reserves, y_reserves, total_supply, t, u=1, c=1):
        """Returns the spot price given the current supply and temporal position along the yield curve"""
        return 1 / pow(c * (y_reserves + total_supply) / (u * x_reserves), t)

    def calc_spot_price_from_apy(self, apy, days_until_maturity):
        """Returns the current spot prcie based on the pool duration and current APY"""
        normalized_pool_duration = days_until_maturity / 365
        return 1 - apy * normalized_pool_duration / 100

    def calc_apy_from_reserves(self, x_reserves, y_reserves, total_supply, t, t_stretch, u=1, c=1):
        """Returns the apy given reserve amounts"""
        spot_price = self.calc_spot_price(x_reserves, y_reserves, total_supply, t, u, c)
        days_until_maturity = t * 365 * t_stretch
        return self.apy(spot_price, days_until_maturity)

    def calc_liquidity(self, target_liquidity, market_price, apy, days_until_maturity, time_stretch, u=1, c=1):
        """Returns the reserve volumes and liquidity amounts"""
        spot_price = self.calc_spot_price_from_apy(apy, days_until_maturity)
        t = days_until_maturity / (365 * time_stretch)
        y_reserves = target_liquidity / market_price / 2 / (1 - apy / 100 * t)
        x_reserves = self.calc_x_reserves(
                apy, y_reserves, days_until_maturity, time_stretch, u, c)
        scale_up_factor = target_liquidity / (x_reserves * market_price + y_reserves * market_price * spot_price)
        y_reserves = y_reserves * scale_up_factor
        x_reserves = x_reserves * scale_up_factor
        liquidity = x_reserves * market_price + y_reserves * market_price * spot_price
        if self.verbose:
            actual_apy = self.calc_apy_from_reserves(
                x_reserves, y_reserves, x_reserves + y_reserves, t, time_stretch, u, c)
            print(f'x={x_reserves} y={y_reserves} total={liquidity} apy={actual_apy}')
        return (x_reserves, y_reserves, liquidity)

    def calc_x_reserves(self, apy, y_reserves, days_until_maturity, time_stretch, u, c):
        """Returns the assumed x reserve amounts given the y reserves and APY"""
        time_stretch_exp = 1 / (days_until_maturity / (365 * time_stretch))
        normalized_pool_duration = days_until_maturity / 365
        apy_decimal = apy / 100
        result = 2 * c * y_reserves / (u * (-1 / (apy_decimal * normalized_pool_duration - 1))**(time_stretch_exp) - c)
        if self.verbose:
            print(f'calc_x_reserves result: {result}')
        return result


class ElementPricingModel(PricingModel):
    """
    Element v1 pricing model

    Does not use the Yield Bearing Vault `u` and `c` variables.
    """

    def model_name(self):
        return "Element"

    def calc_in_given_out(self, out, in_reserves, out_reserves, token_in, g, t, u=1, c=1):
        k = self.calc_k_const(in_reserves, out_reserves, t) # in_reserves**(1 - t) + out_reserves**(1 - t)
        without_fee = pow(k - pow(out_reserves - out, 1 - t), 1 / (1 - t)) - in_reserves
        if token_in == "base":
            fee = (out - without_fee) * g
        elif token_in == "fyt":
            fee = (without_fee - out) * g
        with_fee = without_fee + fee
        without_fee_or_slippage = out * (in_reserves / out_reserves)**t
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_out_given_in(self, in_, in_reserves, out_reserves, token_out, g, t, u=1, c=1):
        k = self.calc_k_const(in_reserves, out_reserves, t) # in_reserves**(1 - t) + out_reserves**(1 - t)
        without_fee = out_reserves - pow(k - pow(in_reserves + in_, 1 - t), 1 / (1 - t))
        if token_out == "base":
            fee = g * (in_ - without_fee)
        elif token_out == "fyt":
            fee = g * (without_fee - in_)
        with_fee = without_fee - fee
        without_fee_or_slippage = in_ / (in_reserves / out_reserves)**t
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_x_reserves(self, apy, y_reserves, days_until_maturity, time_stretch, u=1, c=1):
        return super().calc_x_reserves(
            apy, y_reserves, days_until_maturity, time_stretch, u, c)


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

    def calc_in_given_out(self, out, in_reserves, out_reserves, token_in, g, t, u, c):
        scale = c / u
        if token_in == "base": # calc shares in for fyt out
            dy = out
            z = in_reserves / c # convert from x to z (x=cz)
            y = out_reserves
            # AMM math
            k = self.calc_k_const(u * z, y, t, scale)#scale * (u * z)**(1 - t) + y**(1 - t)
            without_fee = (1 / u * ((k - (y - dy)**(1 - t)) / scale)**(1 / (1 - t)) - z) * c
            # Fee math
            fee = (out - without_fee) * g
            with_fee = without_fee + fee
            without_fee_or_slippage = (in_reserves / (c / u * out_reserves))**t * out

        elif token_in == "fyt": # calc fyt in for shares out
            dz = out / c
            z = out_reserves / c # convert from x to z (x=cz)
            y = in_reserves
            # AMM math
            k = self.calc_k_const(u*z, y, t, scale) # scale * (u * z)**(1 - t) + y**(1 - t)
            without_fee = (k - scale * (u * z - u * dz)**(1 - t))**(1 / (1 - t)) - y
            # Fee math
            fee = (without_fee - out) * g
            with_fee = without_fee + fee
            without_fee_or_slippage = ((c / u * in_reserves) / out_reserves)**t * out
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_out_given_in(self, in_, in_reserves, out_reserves, token_out, g, t, u, c):
        scale = c / u # normalized function of vault yields
        if token_out == "base": # calc shares out for fyt in
            dy = in_
            z = out_reserves / c # convert from x to z (x=cz)
            y = in_reserves
            # AMM math
            k = self.calc_k_const(u * z, y, t, scale) # scale * (u * z)**(1 - t) + y**(1 - t)
            without_fee = (z - 1 / u * ((k - (y + dy)**(1 - t)) / scale)**(1 / (1 - t))) * c
            # Fee math
            fee = (in_ - without_fee) * g
            assert fee >= 0, ('ERROR: Fee should not be negative')
            if fee / in_ < self.floor_fee / 100 / 100:
                fee = in_ * self.floor_fee / 100 / 100
            with_fee = without_fee - fee
            without_fee_or_slippage = 1 / ((c / u * in_reserves) / out_reserves)**t * in_

        elif token_out == "fyt": # calc fyt out for shares in
            dz = in_ / c # convert from x to z (x=cz)
            z = in_reserves / c # convert from x to z (x=cz)
            y = out_reserves
            # AMM math
            k = self.calc_k_const(u * z, y, t, scale) # scale * (u * z)**(1 - t) + y**(1 - t)
            without_fee = y - (k - scale * (u * z + u * dz)**(1 - t))**(1 / (1 - t))
            # Fee math
            fee = (without_fee - in_) * g
            assert fee >= 0, ('ERROR: Fee should not be negative')
            if fee / in_ < self.floor_fee / 100 / 100:
                fee = in_ * self.floor_fee / 100 / 100
            with_fee = without_fee - fee
            without_fee_or_slippage = 1 / (in_reserves / (c / u * out_reserves))**t * in_
        return (without_fee_or_slippage, with_fee, without_fee, fee)
