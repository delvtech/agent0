:py:mod:`elfpy.types`
=====================

.. py:module:: elfpy.types

.. autoapi-nested-parse::

   A set of common types used throughtout the simulation codebase.

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.types.TokenType
   elfpy.types.MarketActionType
   elfpy.types.Quantity
   elfpy.types.StretchedTime
   elfpy.types.MarketAction
   elfpy.types.MarketDeltas
   elfpy.types.MarketState
   elfpy.types.AgentTradeResult
   elfpy.types.MarketTradeResult
   elfpy.types.TradeBreakdown
   elfpy.types.TradeResult
   elfpy.types.RandomSimulationVariables
   elfpy.types.SimulationState



Functions
~~~~~~~~~

.. autoapisummary::

   elfpy.types.to_description



Attributes
~~~~~~~~~~

.. autoapisummary::

   elfpy.types.WEI
   elfpy.types.MAX_RESERVES_DIFFERENCE


.. py:function:: to_description(description: str) -> dict[str, str]

   
   A dataclass helper that constructs metadata containing a description.
















   ..
       !! processed by numpydoc !!

.. py:data:: WEI
   :value: 1e-18

   

.. py:data:: MAX_RESERVES_DIFFERENCE
   :value: 20000000000.0

   

.. py:class:: TokenType

   Bases: :py:obj:`enum.Enum`

   
   A type of token
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: BASE
      :value: 'base'

      

   .. py:attribute:: PT
      :value: 'pt'

      


.. py:class:: MarketActionType

   Bases: :py:obj:`enum.Enum`

   
   The descriptor of an action in a market
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: OPEN_LONG
      :value: 'open_long'

      

   .. py:attribute:: OPEN_SHORT
      :value: 'open_short'

      

   .. py:attribute:: CLOSE_LONG
      :value: 'close_long'

      

   .. py:attribute:: CLOSE_SHORT
      :value: 'close_short'

      

   .. py:attribute:: ADD_LIQUIDITY
      :value: 'add_liquidity'

      

   .. py:attribute:: REMOVE_LIQUIDITY
      :value: 'remove_liquidity'

      


.. py:class:: Quantity

   
   An amount with a unit
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: amount
      :type: float

      

   .. py:attribute:: unit
      :type: TokenType

      


.. py:class:: StretchedTime(days: float, time_stretch: float)

   
   A stretched time value with the time stretch
















   ..
       !! processed by numpydoc !!
   .. py:property:: days

      
      Format time as days
















      ..
          !! processed by numpydoc !!

   .. py:property:: normalized_time

      
      Format time as normalized days
















      ..
          !! processed by numpydoc !!

   .. py:property:: stretched_time

      
      Format time as stretched time
















      ..
          !! processed by numpydoc !!

   .. py:property:: time_stretch

      
      The time stretch constant
















      ..
          !! processed by numpydoc !!


.. py:class:: MarketAction

   
   Market action specification
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: action_type
      :type: MarketActionType

      

   .. py:attribute:: trade_amount
      :type: float

      

   .. py:attribute:: wallet_address
      :type: int

      

   .. py:attribute:: mint_time
      :type: float
      :value: 0

      


.. py:class:: MarketDeltas

   
   Specifies changes to values in the market
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: d_base_asset
      :type: float
      :value: 0

      

   .. py:attribute:: d_token_asset
      :type: float
      :value: 0

      

   .. py:attribute:: d_base_buffer
      :type: float
      :value: 0

      

   .. py:attribute:: d_bond_buffer
      :type: float
      :value: 0

      

   .. py:attribute:: d_lp_reserves
      :type: float
      :value: 0

      

   .. py:attribute:: d_share_price
      :type: float
      :value: 0

      


.. py:class:: MarketState

   
   The state of an AMM

   Implements a class for all that that an AMM smart contract would hold or would have access to
   For example, reserve numbers are local state variables of the AMM.  The vault_apr will most
   likely be accessible through the AMM as well.

   .. attribute:: share_reserves

      TODO: fill this in

      :type: float

   .. attribute:: bond_reserves

      TODO: fill this in

      :type: float

   .. attribute:: base_buffer

      TODO: fill this in

      :type: float

   .. attribute:: bond_buffer

      TODO: fill this in

      :type: float

   .. attribute:: lp_reserves

      TODO: fill this in

      :type: float

   .. attribute:: trade_fee_percent

      The percentage of the difference between the amount paid without
      slippage and the amount received that will be added to the input
      as a fee.

      :type: float

   .. attribute:: redemption_fee_percent

      A flat fee applied to the output.  Not used in this equation for Yieldspace.

      :type: float















   ..
       !! processed by numpydoc !!
   .. py:attribute:: share_reserves
      :type: float
      :value: 0.0

      

   .. py:attribute:: bond_reserves
      :type: float
      :value: 0.0

      

   .. py:attribute:: base_buffer
      :type: float
      :value: 0.0

      

   .. py:attribute:: bond_buffer
      :type: float
      :value: 0.0

      

   .. py:attribute:: lp_reserves
      :type: float
      :value: 0.0

      

   .. py:attribute:: vault_apr
      :type: float
      :value: 0.0

      

   .. py:attribute:: share_price
      :type: float
      :value: 1.0

      

   .. py:attribute:: init_share_price
      :type: float
      :value: 1.0

      

   .. py:attribute:: trade_fee_percent
      :type: float
      :value: 0.0

      

   .. py:attribute:: redemption_fee_percent
      :type: float
      :value: 0.0

      

   .. py:method:: apply_delta(delta: MarketDeltas) -> None

      
      Applies a delta to the market state.
















      ..
          !! processed by numpydoc !!


.. py:class:: AgentTradeResult

   
   The result to a user of performing a trade
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: d_base
      :type: float

      

   .. py:attribute:: d_bonds
      :type: float

      


.. py:class:: MarketTradeResult

   
   The result to a market of performing a trade
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: d_base
      :type: float

      

   .. py:attribute:: d_bonds
      :type: float

      


.. py:class:: TradeBreakdown

   
   A granular breakdown of a trade.

   This includes information relating to fees and slippage.















   ..
       !! processed by numpydoc !!
   .. py:attribute:: without_fee_or_slippage
      :type: float

      

   .. py:attribute:: with_fee
      :type: float

      

   .. py:attribute:: without_fee
      :type: float

      

   .. py:attribute:: fee
      :type: float

      


.. py:class:: TradeResult

   
   The result of performing a trade.

   This includes granular information about the trade details,
   including the amount of fees collected and the total delta.
   Additionally, breakdowns for the updates that should be applied
   to the user and the market are computed.















   ..
       !! processed by numpydoc !!
   .. py:attribute:: user_result
      :type: AgentTradeResult

      

   .. py:attribute:: market_result
      :type: MarketTradeResult

      

   .. py:attribute:: breakdown
      :type: TradeBreakdown

      


.. py:class:: RandomSimulationVariables

   
   Random variables to be used during simulation setup & execution
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: target_liquidity
      :type: float

      

   .. py:attribute:: target_pool_apr
      :type: float

      

   .. py:attribute:: trade_fee_percent
      :type: float

      

   .. py:attribute:: redemption_fee_percent
      :type: float

      

   .. py:attribute:: vault_apr
      :type: list

      

   .. py:attribute:: init_vault_age
      :type: float

      

   .. py:attribute:: init_share_price
      :type: float

      


.. py:class:: SimulationState

   
   Simulator state, updated after each trade
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: model_name
      :type: list

      

   .. py:attribute:: run_number
      :type: list

      

   .. py:attribute:: simulation_start_time
      :type: list

      

   .. py:attribute:: day
      :type: list

      

   .. py:attribute:: block_number
      :type: list

      

   .. py:attribute:: daily_block_number
      :type: list

      

   .. py:attribute:: block_timestamp
      :type: list

      

   .. py:attribute:: current_market_datetime
      :type: list

      

   .. py:attribute:: current_market_yearfrac
      :type: list

      

   .. py:attribute:: run_trade_number
      :type: list

      

   .. py:attribute:: market_step_size
      :type: list

      

   .. py:attribute:: position_duration
      :type: list

      

   .. py:attribute:: target_liquidity
      :type: list

      

   .. py:attribute:: trade_fee_percent
      :type: list

      

   .. py:attribute:: redemption_fee_percent
      :type: list

      

   .. py:attribute:: floor_fee
      :type: list

      

   .. py:attribute:: init_vault_age
      :type: list

      

   .. py:attribute:: base_asset_price
      :type: list

      

   .. py:attribute:: pool_apr
      :type: list

      

   .. py:attribute:: num_trading_days
      :type: list

      

   .. py:attribute:: num_blocks_per_day
      :type: list

      

   .. py:attribute:: spot_price
      :type: list

      

   .. py:method:: update_market_state(market_state: MarketState) -> None

      
      Update each entry in the SimulationState's copy for the market state
      by appending to the list for each key, or creating a new key.

      :param market_state: The state variable for the Market class
      :type market_state: MarketState















      ..
          !! processed by numpydoc !!

   .. py:method:: update_agent_wallet(agent: elfpy.agent.Agent) -> None

      
      Update each entry in the SimulationState's copy for the agent wallet state
      by appending to the list for each key, or creating a new key.

      :param agent: An instantiated Agent object
      :type agent: Agent















      ..
          !! processed by numpydoc !!


