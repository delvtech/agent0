:py:mod:`elfpy.pricing_models.base`
===================================

.. py:module:: elfpy.pricing_models.base

.. autoapi-nested-parse::

   The base pricing model.

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.pricing_models.base.PricingModel




.. py:class:: PricingModel

   Bases: :py:obj:`abc.ABC`

   
   Contains functions for calculating AMM variables

   Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class















   ..
       !! processed by numpydoc !!
   .. py:method:: calc_in_given_out(out: elfpy.types.Quantity, market_state: elfpy.types.MarketState, fee_percent: float, time_remaining: elfpy.types.StretchedTime) -> elfpy.types.TradeResult
      :abstractmethod:

      
      Calculate fees and asset quantity adjustments
















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_out_given_in(in_: elfpy.types.Quantity, market_state: elfpy.types.MarketState, fee_percent: float, time_remaining: elfpy.types.StretchedTime) -> elfpy.types.TradeResult
      :abstractmethod:

      
      Calculate fees and asset quantity adjustments
















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_lp_out_given_tokens_in(d_base: float, rate: float, market_state: elfpy.types.MarketState, time_remaining: elfpy.types.StretchedTime) -> tuple[float, float, float]
      :abstractmethod:

      
      Computes the amount of LP tokens to be minted for a given amount of base asset
















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_lp_in_given_tokens_out(d_base: float, rate: float, market_state: elfpy.types.MarketState, time_remaining: elfpy.types.StretchedTime) -> tuple[float, float, float]
      :abstractmethod:

      
      Computes the amount of LP tokens to be minted for a given amount of base asset
















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_tokens_out_given_lp_in(lp_in: float, rate: float, market_state: elfpy.types.MarketState, time_remaining: elfpy.types.StretchedTime) -> tuple[float, float, float]
      :abstractmethod:

      
      Calculate how many tokens should be returned for a given lp addition
















      ..
          !! processed by numpydoc !!

   .. py:method:: model_name() -> str
      :abstractmethod:

      
      Unique name given to the model, can be based on member variable states
















      ..
          !! processed by numpydoc !!

   .. py:method:: model_type() -> str
      :abstractmethod:

      
      Unique identifier given to the model, should be lower snake_cased name
















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_bond_reserves(target_apr: float, share_reserves: float, time_remaining: elfpy.types.StretchedTime, init_share_price: float = 1, share_price: float = 1)

      
      Returns the assumed bond (i.e. token asset) reserve amounts given
      the share (i.e. base asset) reserves and APR

      :param target_apr: Target fixed APR in decimal units (for example, 5% APR would be 0.05)
      :type target_apr: float
      :param share_reserves: base asset reserves in the pool
      :type share_reserves: float
      :param days_remaining: Amount of days left until bond maturity
      :type days_remaining: float
      :param time_stretch: Time stretch parameter, in years
      :type time_stretch: float
      :param init_share_price: Original share price when the pool started
      :type init_share_price: float
      :param share_price: Current share price
      :type share_price: float

      :returns: * *float* -- The expected amount of bonds (token asset) in the pool, given the inputs
                * **.. todo:: TODO** (*Write a test for this function*)















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_share_reserves(target_apr: float, bond_reserves: float, time_remaining: elfpy.types.StretchedTime, init_share_price: float = 1)

      
      Returns the assumed share (i.e. base asset) reserve amounts given
      the bond (i.e. token asset) reserves and APR

      :param target_apr: Target fixed APR in decimal units (for example, 5% APR would be 0.05)
      :type target_apr: float
      :param bond_reserves: token asset (pt) reserves in the pool
      :type bond_reserves: float
      :param days_remaining: Amount of days left until bond maturity
      :type days_remaining: float
      :param time_stretch: Time stretch parameter, in years
      :type time_stretch: float
      :param init_share_price: Original share price when the pool started
      :type init_share_price: float
      :param share_price: Current share price
      :type share_price: float

      :returns: The expected amount of base asset in the pool, calculated from the provided parameters
      :rtype: float















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_liquidity(market_state: elfpy.types.MarketState, target_liquidity: float, target_apr: float, position_duration: elfpy.types.StretchedTime) -> tuple[float, float]

      
      Returns the reserve volumes and total supply

      The scaling factor ensures bond_reserves and share_reserves add
      up to target_liquidity, while keeping their ratio constant (preserves apr).

      total_liquidity = in base terms, used to target liquidity as passed in
      total_reserves  = in arbitrary units (AU), used for yieldspace math

      :param market_state: the state of the market
      :type market_state: MarketState
      :param target_liquidity_usd: amount of liquidity that the simulation is trying to achieve in a given market
      :type target_liquidity_usd: float
      :param target_apr: desired APR for the seeded market
      :type target_apr: float
      :param position_duration: the duration of positions in this market
      :type position_duration: float

      :returns: Tuple that contains (share_reserves, bond_reserves)
                calculated from the provided parameters
      :rtype: (float, float)















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_total_liquidity_from_reserves_and_price(market_state: elfpy.types.MarketState, share_price: float) -> float

      
      Returns the total liquidity in the pool in terms of base

      :param MarketState:
                          The following member variables are used:
                              share_reserves : float
                                  Base asset reserves in the pool
                              bond_reserves : float
                                  Token asset (pt) reserves in the pool
      :type MarketState: MarketState
      :param share_price: Variable (underlying) yield source price
      :type share_price: float

      :returns: * *float* -- Total liquidity in the pool in terms of base, calculated from the provided parameters
                * **.. todo:: TODO** (*Write a test for this function*)















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_spot_price_from_reserves(market_state: elfpy.types.MarketState, time_remaining: elfpy.types.StretchedTime) -> float

      
      Calculates the spot price of base in terms of bonds.

      The spot price is defined as:

      .. math::
          \begin{align}
          p = (\frac{2y + cz}{\mu z})^{-\tau}
          \end{align}

      :param market_state: The reserves and share prices of the pool.
      :type market_state: MarketState
      :param time_remaining: The time remaining for the asset (incorporates time stretch).
      :type time_remaining: StretchedTime

      :returns: The spot price of principal tokens.
      :rtype: float















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_apr_from_reserves(market_state: elfpy.types.MarketState, time_remaining: elfpy.types.StretchedTime) -> float

      
      Returns the apr given reserve amounts
















      ..
          !! processed by numpydoc !!

   .. py:method:: get_max_long(market_state: elfpy.types.MarketState, fee_percent: float, time_remaining: elfpy.types.StretchedTime) -> tuple[float, float]

      
      Calculates the maximum long the market can support using the bisection
      method.

      :param market_state: The reserves and share prices of the pool.
      :type market_state: MarketState
      :param fee_percent: The fee percent charged by the market.
      :type fee_percent: float
      :param time_remaining: The time remaining for the asset (incorporates time stretch).
      :type time_remaining: StretchedTime

      :returns: The maximum amount of base that can be used to purchase bonds.
      :rtype: float















      ..
          !! processed by numpydoc !!

   .. py:method:: get_max_short(market_state: elfpy.types.MarketState, fee_percent: float, time_remaining: elfpy.types.StretchedTime) -> tuple[float, float]

      
      Calculates the maximum short the market can support using the bisection
      method.

      :param market_state: The reserves and share prices of the pool.
      :type market_state: MarketState
      :param fee_percent: The fee percent charged by the market.
      :type fee_percent: float
      :param time_remaining: The time remaining for the asset (incorporates time stretch).
      :type time_remaining: StretchedTime

      :returns: * *float* -- The maximum amount of base that can be used to short bonds.
                * *float* -- The maximum amount of bonds that can be shorted.















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_time_stretch(apr)

      
      Returns fixed time-stretch value based on current apr (as a decimal)
















      ..
          !! processed by numpydoc !!

   .. py:method:: check_input_assertions(quantity: elfpy.types.Quantity, market_state: elfpy.types.MarketState, fee_percent: float, time_remaining: elfpy.types.StretchedTime)

      
      Applies a set of assertions to the input of a trading function.
















      ..
          !! processed by numpydoc !!

   .. py:method:: check_output_assertions(trade_result: elfpy.types.TradeResult)

      
      Applies a set of assertions to a trade result.
















      ..
          !! processed by numpydoc !!


