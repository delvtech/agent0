"""Implements helper functions for setting up a simulation"""
from __future__ import annotations  # types will be strings by default in 3.11

from importlib import import_module
from typing import Any, TYPE_CHECKING, Optional
import logging

import elfpy.simulators as simulators
import elfpy.utils.time as time_utils
import elfpy.markets.hyperdrive as hyperdrive
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel

if TYPE_CHECKING:
    from elfpy.pricing_models.base import PricingModel
    from elfpy.agents import Agent


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
    config.check_vault_apr()  # quick check to make sure the vault apr is correctly set
    # Instantiate the market.
    pricing_model = get_pricing_model(config.pricing_model_name)
    market = get_market(pricing_model, config)
    simulator = simulators.Simulator(config=config, market=market)
    # Instantiate and add the initial LP agent, if desired
    if config.init_lp is True:
        simulator.add_agents([get_init_lp_agent(market, config.target_liquidity)])
    # Initialize the simulator using only the initial LP.
    simulator.collect_and_execute_trades()
    # Add the remaining agents.
    if agents is not None:
        simulator.add_agents(agents)
    return simulator


def get_init_lp_agent(
    market: hyperdrive.Market,
    target_liquidity: float,
) -> Agent:
    r"""Calculate the required deposit amounts and instantiate the LP agent

    Parameters
    ----------
    market : Market
        empty market object
    target_liquidity : float
        target total liquidity for LPer to provide (bonds+shares)
        the result will be within 1e-15% of the target

    Returns
    -------
    init_lp_agent : Agent
        Agent class that will perform the lp initialization action
    """
    current_market_liquidity = market.pricing_model.calc_total_liquidity_from_reserves_and_price(
        market_state=market.market_state, share_price=market.market_state.share_price
    )
    lp_amount = target_liquidity - current_market_liquidity
    init_lp_agent = get_policy("init_lp")(wallet_address=0, budget=lp_amount)
    return init_lp_agent


def get_market(
    pricing_model: PricingModel,
    config: simulators.Config,
    init_target_liquidity: float = 1.0,
) -> hyperdrive.Market:
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
            target_pool_apr : float
                target apr, used for calculating the time stretch
            trade_fee_percent : float
                portion of trades to be collected as fees for LPers, expressed as a decimal
            vault_apr : list
                valut apr per day for the duration of the simulation
    init_target_liquidity : float = 1.0
        initial liquidity for setting up the market
        should be a tiny amount for setting up apr

    Returns
    -------
    Market
        instantiated market without any liquidity (i.e. no shares or bonds)
    """
    position_duration = time_utils.StretchedTime(
        days=config.num_position_days,
        time_stretch=pricing_model.calc_time_stretch(config.target_pool_apr),
        normalizing_constant=config.num_position_days,
    )
    # apr is "annual", so if position durations is not 365
    # then we need to rescale the target apr passed to calc_liquidity
    adjusted_target_apr = config.target_pool_apr * config.num_position_days / 365
    share_reserves_direct, bond_reserves_direct = pricing_model.calc_liquidity(
        market_state=hyperdrive.MarketState(
            share_price=config.init_share_price, init_share_price=config.init_share_price
        ),
        target_liquidity=init_target_liquidity,
        target_apr=adjusted_target_apr,
        position_duration=position_duration,
    )
    market = hyperdrive.Market(
        pricing_model=pricing_model,
        market_state=hyperdrive.MarketState(
            share_reserves=share_reserves_direct,
            bond_reserves=bond_reserves_direct,
            base_buffer=0,
            bond_buffer=0,
            lp_reserves=init_target_liquidity / config.init_share_price,
            init_share_price=config.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=config.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
            vault_apr=config.vault_apr[0],  # yield bearing source apr
            trade_fee_percent=config.trade_fee_percent,  # g
            redemption_fee_percent=config.redemption_fee_percent,
        ),
        position_duration=position_duration,
    )
    return market


def get_pricing_model(model_name: str) -> PricingModel:
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
        pricing_model = HyperdrivePricingModel()
    elif model_name.lower() == "yieldspace":
        pricing_model = YieldSpacePricingModel()
    else:
        raise ValueError(f'pricing_model_name must be "Hyperdrive", or "YieldSpace", not {model_name}')
    return pricing_model


def get_policy(agent_type: str) -> Any:  # TODO: Figure out a better type for output
    """Returns an uninstantiated agent

    Parameters
    ----------
    agent_type : str
        The agent type must correspond to one of the files in src/elfpy/policies

    Returns
    -------
    Uninstantiated agent policy

    """
    return import_module(f"elfpy.agents.policies.{agent_type}").Policy
