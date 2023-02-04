:py:mod:`elfpy.utils.sim_utils`
===============================

.. py:module:: elfpy.utils.sim_utils

.. autoapi-nested-parse::

   Implements helper functions for setting up a simulation

   ..
       !! processed by numpydoc !!


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   elfpy.utils.sim_utils.get_simulator
   elfpy.utils.sim_utils.get_init_lp_agent
   elfpy.utils.sim_utils.get_market
   elfpy.utils.sim_utils.get_pricing_model
   elfpy.utils.sim_utils.override_random_variables



.. py:function:: get_simulator(config: elfpy.utils.config.Config, agents: Optional[list[elfpy.agent.Agent]] = None, random_sim_vars: Optional[elfpy.types.RandomSimulationVariables] = None) -> elfpy.simulators.Simulator

   
   Construct and initialize a simulator with sane defaults

   The simulated market is initialized with an initial LP.

   :param config: the simulator config
   :type config: Config
   :param agents: the agents to that should be used in the simulator
   :type agents: list[Agent]
   :param random_sim_vars: dataclass that contains variables for initiating and running simulations
   :type random_sim_vars: RandomSimulationVariables

   :returns: **simulator** -- instantiated simulator class
   :rtype: Simulator















   ..
       !! processed by numpydoc !!

.. py:function:: get_init_lp_agent(market: elfpy.markets.Market, target_liquidity: float, target_pool_apr: float, trade_fee_percent: float, seed_liquidity: float = 1) -> elfpy.agent.Agent

   
   Calculate the required deposit amounts and instantiate the LP agent

   The required deposit amounts are computed iteratively to determine market reserve levels that achieve
   the target liquidity and APR. To hit the desired ratio, the agent opens a small LP, then a short,
   then a larger LP. Each iteration estimates the slippage due to the short and adjusts the first LP amount
   to account for it. The difference in slippage from one iteration to the next monotonically decreases,
   since it is accounting for diminishing additions to the market share reserves. A more detailed description
   is here: https://github.com/element-fi/elf-simulations/pull/136#issuecomment-1405922764

   :param market: empty market object
   :type market: Market
   :param target_liquidity: target total liquidity for LPer to provide (bonds+shares)
                            the result will be within 1e-15% of the target
   :type target_liquidity: float
   :param target_pool_apr: target pool apr for the market
                           the result will be within 1e-13% of the target
   :type target_pool_apr: float
   :param fee_percent: how much the LPer will collect in fees
   :type fee_percent: float
   :param seed_liquidity: initial (small) liquidity amount for setting the market APR
   :type seed_liquidity: float

   :returns: **init_lp_agent** -- Agent class that will perform the lp initialization action
   :rtype: Agent















   ..
       !! processed by numpydoc !!

.. py:function:: get_market(pricing_model: elfpy.pricing_models.base.PricingModel, target_pool_apr: float, trade_fee_percent: float, redemption_fee_percent: float, position_duration: float, vault_apr: list, init_share_price: float) -> elfpy.markets.Market

   
   Setup market

   :param pricing_model: instantiated pricing model
   :type pricing_model: PricingModel
   :param target_pool_apr: target apr, used for calculating the time stretch
                           NOTE: the market apr will not have this target value until the init_lp agent trades,
                           or the share & bond reserves are explicitly set
   :type target_pool_apr: float
   :param trade_fee_percent: portion of trades to be collected as fees for LPers, expressed as a decimal
   :type trade_fee_percent: float
   :param redemption_fee_percent: portion of redemptions to be collected as fees for LPers, expressed as a decimal
   :type redemption_fee_percent: float
   :param token_duration: how much time between token minting and expiry, in fractions of a year (e.g. 0.5 is 6 months)
   :type token_duration: float
   :param vault_apr: valut apr per day for the duration of the simulation
   :type vault_apr: list
   :param init_share_price: the initial price of the yield bearing vault shares
   :type init_share_price: float

   :returns: * *Market* -- instantiated market without any liquidity (i.e. no shares or bonds)
             * **.. todo:: TODO** (*Rename the fee_percent variable so that it doesn't use "percent"*)















   ..
       !! processed by numpydoc !!

.. py:function:: get_pricing_model(model_name: str) -> elfpy.pricing_models.base.PricingModel

   
   Get a PricingModel object from the config passed in

   :param model_name: name of the desired pricing_model; can be "hyperdrive", or "yieldspace"
   :type model_name: str

   :returns: instantiated pricing model matching the input argument
   :rtype: PricingModel















   ..
       !! processed by numpydoc !!

.. py:function:: override_random_variables(random_variables: elfpy.types.RandomSimulationVariables, override_dict: dict[str, Any]) -> elfpy.types.RandomSimulationVariables

   
   Override the random simulation variables with targeted values, as specified by the keys

   :param random_variables: dataclass that contains variables for initiating and running simulations
   :type random_variables: RandomSimulationVariables
   :param override_dict: dictionary containing keys that correspond to member fields of the RandomSimulationVariables class
   :type override_dict: dict

   :returns: same dataclass as the random_variables input, but with fields specified by override_dict changed
   :rtype: RandomSimulationVariables















   ..
       !! processed by numpydoc !!

