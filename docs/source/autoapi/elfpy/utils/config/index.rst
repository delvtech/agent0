:py:mod:`elfpy.utils.config`
============================

.. py:module:: elfpy.utils.config

.. autoapi-nested-parse::

   Config structure

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.utils.config.MarketConfig
   elfpy.utils.config.AMMConfig
   elfpy.utils.config.SimulatorConfig
   elfpy.utils.config.Config



Functions
~~~~~~~~~

.. autoapisummary::

   elfpy.utils.config.setup_vault_apr
   elfpy.utils.config.get_random_variables



.. py:class:: MarketConfig

   
   config parameters specific to the market
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: min_target_liquidity
      :type: float

      

   .. py:attribute:: max_target_liquidity
      :type: float

      

   .. py:attribute:: min_target_volume
      :type: float

      

   .. py:attribute:: max_target_volume
      :type: float

      

   .. py:attribute:: min_vault_age
      :type: int

      

   .. py:attribute:: max_vault_age
      :type: int

      

   .. py:attribute:: vault_apr
      :type: Union[Callable, dict]

      

   .. py:attribute:: base_asset_price
      :type: float

      


.. py:class:: AMMConfig

   
   config parameters specific to the amm
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: pricing_model_name
      :type: str

      

   .. py:attribute:: min_fee
      :type: float

      

   .. py:attribute:: max_fee
      :type: float

      

   .. py:attribute:: min_pool_apr
      :type: float

      

   .. py:attribute:: max_pool_apr
      :type: float

      

   .. py:attribute:: floor_fee
      :type: float

      


.. py:class:: SimulatorConfig

   
   config parameters specific to the simulator
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: num_trading_days
      :type: int

      

   .. py:attribute:: num_blocks_per_day
      :type: int

      

   .. py:attribute:: num_position_days
      :type: float

      

   .. py:attribute:: shuffle_users
      :type: bool

      

   .. py:attribute:: agent_policies
      :type: list

      

   .. py:attribute:: init_lp
      :type: bool

      

   .. py:attribute:: compound_vault_apr
      :type: bool

      

   .. py:attribute:: init_vault_age
      :type: float

      

   .. py:attribute:: logging_level
      :type: str

      

   .. py:attribute:: precision
      :type: int

      

   .. py:attribute:: random_seed
      :type: int

      

   .. py:attribute:: rng
      :type: numpy.random.Generator

      


.. py:class:: Config

   
   Data object for storing user simulation config parameters
















   ..
       !! processed by numpydoc !!
   .. py:attribute:: market
      :type: MarketConfig

      

   .. py:attribute:: amm
      :type: AMMConfig

      

   .. py:attribute:: simulator
      :type: SimulatorConfig

      


.. py:function:: setup_vault_apr(config: Config)

   
   Construct the vault_apr list
   Note: callable type option would allow for infinite num_trading_days after small modifications

   :param config: config object, as defined in elfpy.utils.config
   :type config: Config

   :returns: **vault_apr** -- list of apr values that is the same length as num_trading_days
   :rtype: list















   ..
       !! processed by numpydoc !!

.. py:function:: get_random_variables(config: Config)

   
   Use random number generator to assign initial simulation parameter values

   :param config: config object, as defined in elfpy.utils.config
   :type config: Config

   :returns: dataclass that contains variables for initiating and running simulations
   :rtype: RandomSimulationVariables















   ..
       !! processed by numpydoc !!

