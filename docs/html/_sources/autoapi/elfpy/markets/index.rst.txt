:py:mod:`elfpy.markets`
=======================

.. py:module:: elfpy.markets

.. autoapi-nested-parse::

   Market simulators store state information when interfacing AMM pricing models with users.

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.markets.Market




.. py:class:: Market(pricing_model: elfpy.pricing_models.base.PricingModel, market_state: elfpy.types.MarketState = MarketState(share_reserves=0, bond_reserves=0, base_buffer=0, bond_buffer=0, lp_reserves=0, vault_apr=0, share_price=1, init_share_price=1, trade_fee_percent=0, redemption_fee_percent=0), position_duration: elfpy.types.StretchedTime = StretchedTime(365, 1))

   
   Market state simulator

   Holds state variables for market simulation and executes trades.
   The Market class executes trades by updating market variables according to the given pricing model.
   It also has some helper variables for assessing pricing model values given market conditions.















   ..
       !! processed by numpydoc !!
   .. py:property:: rate

      
      Returns the current market apr
















      ..
          !! processed by numpydoc !!

   .. py:property:: spot_price

      
      Returns the current market price of the share reserves
















      ..
          !! processed by numpydoc !!

   .. py:method:: check_action_type(action_type: elfpy.types.MarketActionType, pricing_model_name: str) -> None

      
      Ensure that the agent action is an allowed action for this market

      :param action_type: See MarketActionType for all acceptable actions that can be performed on this market
      :type action_type: MarketActionType
      :param pricing_model_name: The name of the pricing model, must be "hyperdrive" or "yieldspace"
      :type pricing_model_name: str

      :rtype: None















      ..
          !! processed by numpydoc !!

   .. py:method:: trade_and_update(agent_action: elfpy.types.MarketAction) -> elfpy.wallet.Wallet

      
      Execute a trade in the simulated market

      check which of 6 action types are being executed, and handles each case:

      open_long

      close_long

      open_short

      close_short

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















      ..
          !! processed by numpydoc !!

   .. py:method:: update_market(market_deltas: elfpy.types.MarketDeltas) -> None

      
      Increments member variables to reflect current market conditions

      .. todo:: This order is weird. We should move everything in apply_update to update_market,
          and then make a new function called check_update that runs these checks















      ..
          !! processed by numpydoc !!

   .. py:method:: get_market_state_string() -> str

      
      Returns a formatted string containing all of the Market class member variables
















      ..
          !! processed by numpydoc !!

   .. py:method:: tick(delta_time: float) -> None

      
      Increments the time member variable
















      ..
          !! processed by numpydoc !!

   .. py:method:: open_short(wallet_address: int, trade_amount: float) -> tuple[elfpy.types.MarketDeltas, elfpy.wallet.Wallet]

      
      shorts need their margin account to cover the worst case scenario (p=1)
      margin comes from 2 sources:
      - the proceeds from your short sale (p)
      - the max value you cover with base deposted from your wallet (1-p)
      these two components are both priced in base, yet happily add up to 1.0 units of bonds
      so we have the following identity:
      total margin (base, from proceeds + deposited) = face value of bonds shorted (# of bonds)

      this guarantees that bonds in the system are always fully backed by an equal amount of base















      ..
          !! processed by numpydoc !!

   .. py:method:: close_short(wallet_address: int, trade_amount: float, mint_time: float) -> tuple[elfpy.types.MarketDeltas, elfpy.wallet.Wallet]

      
      when closing a short, the number of bonds being closed out, at face value, give us the total margin returned
      the worst case scenario of the short is reduced by that amount, so they no longer need margin for it
      at the same time, margin in their account is drained to pay for the bonds being bought back
      so the amount returned to their wallet is trade_amount minus the cost of buying back the bonds
      that is, d_base = trade_amount (# of bonds) + trade_result.user_result.d_base (a negative amount, in base))
      for more on short accounting, see the open short method
















      ..
          !! processed by numpydoc !!

   .. py:method:: open_long(wallet_address: int, trade_amount: float) -> tuple[elfpy.types.MarketDeltas, elfpy.wallet.Wallet]

      
      take trade spec & turn it into trade details
      compute wallet update spec with specific details
      will be conditional on the pricing model
















      ..
          !! processed by numpydoc !!

   .. py:method:: close_long(wallet_address: int, trade_amount: float, mint_time: float) -> tuple[elfpy.types.MarketDeltas, elfpy.wallet.Wallet]

      
      take trade spec & turn it into trade details
      compute wallet update spec with specific details
      will be conditional on the pricing model
















      ..
          !! processed by numpydoc !!

   .. py:method:: add_liquidity(wallet_address: int, trade_amount: float) -> tuple[elfpy.types.MarketDeltas, elfpy.wallet.Wallet]

      
      Computes new deltas for bond & share reserves after liquidity is added
















      ..
          !! processed by numpydoc !!

   .. py:method:: remove_liquidity(wallet_address: int, trade_amount: float) -> tuple[elfpy.types.MarketDeltas, elfpy.wallet.Wallet]

      
      Computes new deltas for bond & share reserves after liquidity is removed
















      ..
          !! processed by numpydoc !!

   .. py:method:: log_market_step_string() -> None

      
      Logs the current market step
















      ..
          !! processed by numpydoc !!


