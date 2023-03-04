"""Implements helper functions for setting up a simulation"""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from importlib import import_module
from typing import TYPE_CHECKING, Any, Optional

import elfpy.simulators as simulators
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.time as time
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.pricing_models.yieldspace as yieldspace_pm

if TYPE_CHECKING:
    import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
    import elfpy.agents.wallet as wallet
    from elfpy.agents.agent import Agent


def get_simulator(
    config: simulators.Config,
    agents: Optional[list[Agent]] = None,
) -> simulators.Simulator:
    r"""Construct and initialize a simulator with sane defaults

    The simulated market is initialized with an initial LP.

    Parameters
    ----------
    config : Config
        the simulator config
    agents : Optional[list[Agent]]
        the agents to that should be used in the simulator

    Returns
    -------
    simulator : Simulator
        instantiated simulator class
    """
    config.check_variable_apr()  # quick check to make sure the vault apr is correctly set
    # Instantiate the market.
    pricing_model = get_pricing_model(config.pricing_model_name)
    block_time = time.BlockTime()
    market, init_agent_deltas, market_deltas = get_initialized_hyperdrive_market(pricing_model, block_time, config)
    simulator = simulators.Simulator(config=config, market=market, block_time=block_time)
    # Instantiate and add the initial LP agent, if desired
    if config.init_lp:
        init_agent = get_policy("init_lp")(wallet_address=0, budget=0)
        init_agent.wallet.update(init_agent_deltas)
        simulator.add_agents([init_agent])
    if config.do_dataframe_states:
        # update state with day & block = 0 for the initialization trades
        simulator.new_simulation_state.update(
            run_vars=simulators.RunSimVariables(
                run_number=simulator.run_number,
                config=config,
                agent_init=[agent.wallet for agent in simulator.agents.values()],
                market_init=simulator.market.market_state,
                time_step=simulator.time_step,
                position_duration=simulator.market.position_duration,
            ),
            day_vars=simulators.DaySimVariables(
                run_number=simulator.run_number,
                day=simulator.day,
                variable_apr=simulator.market.market_state.variable_apr,
                share_price=simulator.market.market_state.share_price,
            ),
            block_vars=simulators.BlockSimVariables(
                run_number=simulator.run_number,
                day=simulator.day,
                block_number=simulator.block_number,
                time=simulator.block_time.time,
            ),
        )
        # TODO: init_lp_agent should execute a trade that calls initialize market
        # issue # 268
        if config.init_lp:
            if config.do_dataframe_states:
                simulator.new_simulation_state.update(
                    trade_vars=simulators.TradeSimVariables(
                        run_number=simulator.run_number,
                        day=simulator.day,
                        block_number=simulator.block_number,
                        trade_number=0,
                        fixed_apr=simulator.market.fixed_apr,
                        spot_price=simulator.market.spot_price,
                        market_deltas=market_deltas,
                        agent_address=0,
                        agent_deltas=init_agent_deltas,
                    )
                )
            simulator.update_simulation_state()
            simulator.trade_number += 1
    # Add the remaining agents.
    if agents is not None:
        simulator.add_agents(agents)
    return simulator


def get_initialized_hyperdrive_market(
    pricing_model: hyperdrive_pm.HyperdrivePricingModel | yieldspace_pm.YieldspacePricingModel,
    block_time: time.BlockTime,
    config: simulators.Config,
) -> tuple[hyperdrive_market.Market, wallet.Wallet, hyperdrive_actions.MarketDeltas]:
    r"""Setup market

    Parameters
    ----------
    pricing_model : PricingModel
        instantiated pricing model
    config: Config
        instantiated config object. The following attributes are used:
            init_share_price : float
                the initial price of the yield bearing vault shares
            num_position_days : int
                how much time between token minting and expiry, in days
            redemption_fee_percent : float
                portion of redemptions to be collected as fees for LPers, expressed as a decimal
            target_fixed_apr : float
                target apr, used for calculating the time stretch
            trade_fee_percent : float
                portion of trades to be collected as fees for LPers, expressed as a decimal
            variable_apr : list
                variable (often a valut) apr per day for the duration of the simulation

    Returns
    -------
    Market
        instantiated market without any liquidity (i.e. no shares or bonds)
    """
    position_duration = time.StretchedTime(
        days=config.num_position_days,
        time_stretch=pricing_model.calc_time_stretch(config.target_fixed_apr),
        normalizing_constant=config.num_position_days,
    )
    market = hyperdrive_market.Market(
        pricing_model=pricing_model,
        block_time=block_time,
        market_state=hyperdrive_market.MarketState(
            init_share_price=config.init_share_price,
            share_price=config.init_share_price,
            variable_apr=config.variable_apr[0],
            trade_fee_percent=config.trade_fee_percent,
            redemption_fee_percent=config.redemption_fee_percent,
        ),
        position_duration=position_duration,
    )
    # Not using an agent to initialize the market so we ignore the agent address
    market_deltas, agent_deltas = market.initialize(
        wallet_address=0,
        contribution=config.target_liquidity,
        target_apr=config.target_fixed_apr,
    )
    return market, agent_deltas, market_deltas


def get_pricing_model(model_name: str) -> yieldspace_pm.YieldspacePricingModel | hyperdrive_pm.HyperdrivePricingModel:
    r"""Get a PricingModel object from the config passed in

    Parameters
    ----------
    model_name : str
        name of the desired pricing_model; can be "hyperdrive", or "yieldspace"

    Returns
    -------
    PricingModel
        instantiated pricing model matching the input argument
    """
    logging.info("%s %s %s", "#" * 20, model_name, "#" * 20)
    if model_name.lower() == "hyperdrive":
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
    elif model_name.lower() == "yieldspace":
        pricing_model = yieldspace_pm.YieldspacePricingModel()
    else:
        raise ValueError(f'pricing_model_name must be "Hyperdrive", or "YieldSpace", not {model_name}')
    return pricing_model


def get_policy(agent_type: str) -> Any:  # TODO: Figure out a better type for output
    """Returns an uninstantiated agent

    Parameters
    ----------
    agent_type : str
        The agent type must correspond to one of the files in elfpy.policies

    Returns
    -------
    Uninstantiated agent policy

    """
    return import_module(f"elfpy.agents.policies.{agent_type}").Policy
