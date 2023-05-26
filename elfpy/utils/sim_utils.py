"""Implements helper functions for setting up a simulation"""
from __future__ import annotations

from typing import TYPE_CHECKING
from elfpy.agents.policies.init_lp import InitializeLiquidityAgent

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.simulators as simulators
import elfpy.time as time
from elfpy.math import FixedPoint

if TYPE_CHECKING:
    import elfpy.agents.wallet as wallet
    import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
    from elfpy.agents.agent import Agent


def get_simulator_fp(config: simulators.ConfigFP, agents: list[Agent] | None = None) -> simulators.SimulatorFP:
    r"""Construct and initialize a simulator with sane defaults

    The simulated market is initialized with an initial LP.

    Arguments
    ---------
    config : Config
        the simulator config
    agents : list[Agent] | None
        the agents to that should be used in the simulator

    Returns
    -------
    simulator : Simulator
        instantiated simulator class
    """
    config.check_variable_apr()  # quick check to make sure the vault apr is correctly set
    # Instantiate the market.
    # pricing model is hardcoded for now.  once we have support for more markets, we can add a
    # config option for type of market
    pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
    block_time = time.BlockTimeFP()
    market, init_agent_deltas, market_deltas = get_initialized_hyperdrive_market_fp(pricing_model, block_time, config)
    simulator = simulators.SimulatorFP(config=config, market=market, block_time=block_time)
    # Instantiate and add the initial LP agent, if desired
    if config.init_lp:
        init_agent = InitializeLiquidityAgent(wallet_address=0, budget=FixedPoint(config.target_liquidity))
        init_agent_action = init_agent.action(market)[0]
        init_agent.wallet.update(init_agent_deltas)
        simulator.add_agents([init_agent])
    if config.do_dataframe_states:
        # update state with day & block = 0 for the initialization trades
        simulator.new_simulation_state.update(
            run_vars=simulators.RunSimVariablesFP(
                run_number=simulator.run_number,
                config=config,
                agent_init=[agent.wallet for agent in simulator.agents.values()],
                market_init=simulator.market.market_state,
                time_step=simulator.time_step,
                position_duration=simulator.market.position_duration,
            ),
            day_vars=simulators.DaySimVariablesFP(
                run_number=simulator.run_number,
                day=simulator.day,
                variable_apr=float(simulator.market.market_state.variable_apr),
                share_price=float(simulator.market.market_state.share_price),
            ),
            block_vars=simulators.BlockSimVariablesFP(
                run_number=simulator.run_number,
                day=simulator.day,
                block_number=simulator.block_number,
                time=float(simulator.block_time.time),
            ),
        )
        # TODO: init_lp_agent should execute a trade that calls initialize market
        # issue # 268
        if config.init_lp:
            if config.do_dataframe_states:
                simulator.new_simulation_state.update(
                    trade_vars=simulators.TradeSimVariablesFP(
                        run_number=simulator.run_number,
                        day=simulator.day,
                        block_number=simulator.block_number,
                        trade_number=0,
                        fixed_apr=float(simulator.market.fixed_apr),
                        spot_price=float(simulator.market.spot_price),
                        trade_action=init_agent_action.trade,  # type: ignore # pylint: disable=unexpected-keyword-arg
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


def get_initialized_hyperdrive_market_fp(
    pricing_model: hyperdrive_pm.HyperdrivePricingModelFP,
    block_time: time.BlockTimeFP,
    config: simulators.ConfigFP,
) -> tuple[hyperdrive_market.MarketFP, wallet.WalletFP, hyperdrive_actions.MarketDeltasFP]:
    r"""Setup market

    Arguments
    ----------
    pricing_model : PricingModel
        instantiated pricing model
    block_time : BlockTime
        instantiated global time object
    config: Config
        instantiated config object. The following attributes are used:
            init_share_price : float
                the initial price of the yield bearing vault shares
            num_position_days : int
                how much time between token minting and expiry, in days
            flat_fee_multiple : float
                portion of flats to be collected as fees for LPers, expressed as a decimal
            target_fixed_apr : float
                target apr, used for calculating the time stretch
            curve_fee_multiple : float
                portion of trades to be collected as fees for LPers, expressed as a decimal
            variable_apr : list[float]
                variable (often a valut) apr per day for the duration of the simulation

    Returns
    -------
    Market
        instantiated market without any liquidity (i.e. no shares or bonds)
    Wallet
        wallet deltas for the initial LP
    MarketDeltas
        market deltas for the initial LP
    """
    position_duration = time.StretchedTimeFP(
        days=FixedPoint(config.num_position_days * 10**18),
        time_stretch=pricing_model.calc_time_stretch(FixedPoint(config.target_fixed_apr)),
        normalizing_constant=FixedPoint(config.num_position_days * 10**18),
    )
    market = hyperdrive_market.MarketFP(
        pricing_model=pricing_model,
        block_time=block_time,
        market_state=hyperdrive_market.MarketStateFP(
            init_share_price=FixedPoint(config.init_share_price),
            share_price=FixedPoint(config.init_share_price),
            variable_apr=FixedPoint(config.variable_apr[0]),
            curve_fee_multiple=FixedPoint(config.curve_fee_multiple),
            flat_fee_multiple=FixedPoint(config.flat_fee_multiple),
        ),
        position_duration=position_duration,
    )
    # Not using an agent to initialize the market so we ignore the agent address
    market_deltas, agent_deltas = market.initialize(
        wallet_address=0,
        contribution=FixedPoint(config.target_liquidity),
        target_apr=FixedPoint(config.target_fixed_apr),
    )
    return market, agent_deltas, market_deltas
