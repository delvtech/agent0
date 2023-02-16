
    def execute_trades(self, agent_trades: list[tuple[int, MarketAction]]) -> None:
        r"""Execute a list of trades associated with agents in the simulator.

        Parameters
        ----------
        agent_trades : list[tuple[int, list[MarketAction]]]
            A list of agent trades. These will be executed in a random order.
            for example [(0,trade), (1,trade_1)]
        """
        # create a process pool that uses all cpus
        # with multiprocessing.Pool() as pool:
        #    # loop over each agent trade
        #    for agent_market_deltas in pool.imap(self.market.trade_and_update, agent_trades):
        #        (
        #            agent_id,
        #            trade,
        #            agent_deltas,
        #            market_deltas,
        #        ) = agent_market_deltas
        #        agent = self.agents[agent_id]
        #        self.market.update_market(market_deltas)
        #        agent.update_wallet(agent_deltas, self.market)
        #        agent.log_status_report()
        #        self.update_simulation_state(
        #            who_traded=agent_id,
        #            agent_name=self.agents[agent_id].name,
        #            trade=trade,
        #            agent_deltas=agent_deltas,
        #        )
        #        logging.debug(
        #            "agent #%g wallet deltas:\n%s",
        #            agent.wallet.address,
        #            agent_deltas,
        #        )
        #        self.run_trade_number += 1

        for agent_id, trade in agent_trades:
            agent = self.agents[agent_id]
            _, _, agent_deltas, market_deltas = self.market.trade_and_update((agent_id, trade))
            self.market.update_market(market_deltas)
            agent.update_wallet(agent_deltas, self.market)
            # TODO: Get simulator, market, pricing model, agent state strings and log
            # FIXME: need to log deaggregated trade informaiton, i.e. trade_deltas
            agent.log_status_report()
            self.update_simulation_state(
                who_traded=agent_id, agent_name=self.agents[agent_id].name, trade=trade, agent_deltas=agent_deltas
            )
            logging.debug(
                "agent #%g wallet deltas:\n%s",
                agent.wallet.address,
                agent_deltas,
            )
            self.run_trade_number += 1

    def trade_and_update(self, action_details: tuple[int, MarketAction]) -> tuple[int, MarketDeltas, Wallet]:
        r"""Execute a trade in the simulated market

        check which of 6 action types are being executed, and handles each case:

        TODO: initialize_market

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
        """
        agent_id, agent_action = action_details
        # TODO: add use of the Quantity type to enforce units while making it clear what units are being used
        self.check_action_type(agent_action.action_type, self.pricing_model.model_name())
        # for each position, specify how to forumulate trade and then execute
        # TODO:
        # if agent_action.action_type == MarketActionType.INITIALIZE_MARKET:
        #    market_deltas, agent_deltas = self.initialize_market(
        #        wallet_address=agent_action.wallet_address,
        #        contribution=agent_action.trade_amount,
        #        # TODO: The agent should be able to specify the APR. We can
        #        # also do this at construction which may be preferable.
        #        target_apr=0.05,
        #    )
        if agent_action.action_type == MarketActionType.OPEN_LONG:  # buy PT to open long
            market_deltas, agent_deltas = self.open_long(
                wallet_address=agent_action.wallet_address,
                trade_amount=agent_action.trade_amount,  # in base: that's the thing in your wallet you want to sell
            )
        elif agent_action.action_type == MarketActionType.CLOSE_LONG:  # sell to close long
            market_deltas, agent_deltas = self.close_long(
                wallet_address=agent_action.wallet_address,
                trade_amount=agent_action.trade_amount,  # in bonds: that's the thing in your wallet you want to sell
                mint_time=agent_action.mint_time,
            )
        elif agent_action.action_type == MarketActionType.OPEN_SHORT:  # sell PT to open short
            market_deltas, agent_deltas = self.open_short(
                wallet_address=agent_action.wallet_address,
                trade_amount=agent_action.trade_amount,  # in bonds: that's the thing you want to short
            )
        elif agent_action.action_type == MarketActionType.CLOSE_SHORT:  # buy PT to close short
            assert (
                agent_action.open_share_price is not None
            ), "ERROR: agent_action.open_share_price must be provided when closing a short"
            market_deltas, agent_deltas = self.close_short(
                wallet_address=agent_action.wallet_address,
                trade_amount=agent_action.trade_amount,  # in bonds: that's the thing you owe, and need to buy back
                mint_time=agent_action.mint_time,
                open_share_price=agent_action.open_share_price,
            )
        elif agent_action.action_type == MarketActionType.ADD_LIQUIDITY:
            market_deltas, agent_deltas = self.add_liquidity(
                wallet_address=agent_action.wallet_address,
                trade_amount=agent_action.trade_amount,
            )
        elif agent_action.action_type == MarketActionType.REMOVE_LIQUIDITY:
            market_deltas, agent_deltas = self.remove_liquidity(
                wallet_address=agent_action.wallet_address,
                trade_amount=agent_action.trade_amount,
            )
        else:
            raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
        logging.debug(
            "%s\n%s\nagent_deltas = %s\npre_trade_market = %s",
            agent_action,
            market_deltas,
            agent_deltas,
            self.market_state,
        )
        # self.update_market(market_deltas)
        return (agent_id, agent_action, agent_deltas, market_deltas)