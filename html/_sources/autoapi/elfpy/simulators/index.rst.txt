:py:mod:`elfpy.simulators`
==========================

.. py:module:: elfpy.simulators

.. autoapi-nested-parse::

   Simulator class wraps the pricing models and markets for experiment tracking and execution

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.simulators.Simulator




.. py:class:: Simulator(config: elfpy.utils.config.Config, market: elfpy.markets.Market, random_simulation_variables: Optional[elfpy.types.RandomSimulationVariables] = None)

   
   Stores environment variables & market simulation outputs for AMM experimentation

   Member variables include input settings, random variable ranges, and simulation outputs.
   To be used in conjunction with the Market and PricingModel classes















   ..
       !! processed by numpydoc !!
   .. py:method:: check_vault_apr() -> None

      
      Verify that the vault_apr is the right length
















      ..
          !! processed by numpydoc !!

   .. py:method:: set_rng(rng: numpy.random._generator.Generator) -> None

      
      Assign the internal random number generator to a new instantiation
      This function is useful for forcing identical trade volume and directions across simulation runs

      :param rng: Random number generator, constructed using np.random.default_rng(seed)
      :type rng: Generator















      ..
          !! processed by numpydoc !!

   .. py:method:: log_config_variables() -> None

      
      Prints all variables that are in config
















      ..
          !! processed by numpydoc !!

   .. py:method:: get_simulation_state_string() -> str

      
      Returns a formatted string containing all of the Simulation class member variables

      :returns: **state_string** -- Simulator class member variables (keys & values in self.__dict__) cast to a string, separated by a new line
      :rtype: str















      ..
          !! processed by numpydoc !!

   .. py:method:: market_step_size() -> float

      
      Returns minimum time increment

      :returns: time between blocks, which is computed as 1 / blocks_per_year
      :rtype: float















      ..
          !! processed by numpydoc !!

   .. py:method:: add_agents(agent_list: list[elfpy.agent.Agent]) -> None

      
      Append the agents and simulation_state member variables

      If trades have already happened (as indicated by self.run_trade_number), then empty wallet states are
      prepended to the simulation_state for each new agent so that the state can still easily be converted into
      a pandas dataframe.

      :param agent_list: A list of instantiated Agent objects
      :type agent_list: list[Agent]















      ..
          !! processed by numpydoc !!

   .. py:method:: collect_and_execute_trades(last_block_in_sim: bool = False) -> None

      
      Get trades from the agent list, execute them, and update states

      :param last_block_in_sim: If True, indicates if the current set of trades are occuring on the final block in the simulation
      :type last_block_in_sim: bool















      ..
          !! processed by numpydoc !!

   .. py:method:: collect_trades(agent_ids: Any) -> list[tuple[int, list[elfpy.types.MarketAction]]]

      
      Collect trades from a set of provided agent IDs.

      :param agent_ids: A list of agent IDs. These IDs must correspond to agents that are
                        registered in the simulator.
      :type agent_ids: Any

      :returns: A list of trades associated with specific agents.
      :rtype: list[tuple[int, list[MarketAction]]]















      ..
          !! processed by numpydoc !!

   .. py:method:: collect_liquidation_trades(agent_ids: Any) -> list[tuple[int, list[elfpy.types.MarketAction]]]

      
      Collect liquidation trades from a set of provided agent IDs.

      :param agent_ids: A list of agent IDs. These IDs must correspond to agents that are
                        registered in the simulator.
      :type agent_ids: Any

      :returns: A list of liquidation trades associated with specific agents.
      :rtype: list[tuple[int, list[MarketAction]]]















      ..
          !! processed by numpydoc !!

   .. py:method:: execute_trades(trades: list[tuple[int, list[elfpy.types.MarketAction]]]) -> None

      
      Execute a list of trades associated with agents in the simulator.

      :param trades: A list of agent trades. These will be executed in order.
      :type trades: list[tuple[int, list[MarketAction]]]















      ..
          !! processed by numpydoc !!

   .. py:method:: run_simulation() -> None

      
      Run the trade simulation and update the output state dictionary

      This is the primary function of the Simulator class.
      The PricingModel and Market objects will be constructed.
      A loop will execute a group of trades with random volumes and directions for each day,
      up to `self.config.simulator.num_trading_days` days.

      :rtype: There are no returns, but the function does update the simulation_state member variable















      ..
          !! processed by numpydoc !!

   .. py:method:: update_simulation_state() -> None

      
      Increment the list for each key in the simulation_state output variable
















      ..
          !! processed by numpydoc !!


