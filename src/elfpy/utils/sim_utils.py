"""Implements helper functions for setting up a simulation"""
from __future__ import annotations  # types will be strings by default in 3.11

from importlib import import_module
from typing import Any, TYPE_CHECKING, Optional
import logging

from elfpy.simulators import Simulator
from elfpy.types import (
    MarketState,
    Quantity,
    StretchedTime,
    TokenType,
)
from elfpy.markets import Market
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel

if TYPE_CHECKING:
    from elfpy.pricing_models.base import PricingModel
    from elfpy.agent import Agent
    from elfpy.types import Config


def get_simulator(
    config: Config,
    agents: Optional[list[Agent]] = None,
) -> Simulator:
    r"""Construct and initialize a simulator with sane defaults

    The simulated market is initialized with an initial LP.

    Parameters
    ----------
    config : Config
        the simulator config
    agents : list[Agent]
        the agents to that should be used in the simulator
    random_sim_vars : RandomSimulationVariables
        dataclass that contains variables for initiating and running simulations
    override_dict : dict
        dictionary containing keys that correspond to member fields of the RandomSimulationVariables class

    Returns
    -------
    simulator : Simulator
        instantiated simulator class
    """
    config.check_vault_apr()  # quick check to make sure the vault apr is correctly set
    # Instantiate the market.
    pricing_model = get_pricing_model(config.pricing_model_name)
    market = get_market(pricing_model, config)
    simulator = Simulator(config=config, market=market)
    # Instantiate and add the initial LP agent, if desired
    if config.init_lp is True:
        init_agents = [
            get_init_lp_agent(market, config.target_liquidity, config.target_pool_apr, config.trade_fee_percent)
        ]
        simulator.add_agents(init_agents)
    # Initialize the simulator using only the initial LP.
    simulator.collect_and_execute_trades()
    # Add the remaining agents.
    if agents is not None:
        simulator.add_agents(agents)
    return simulator


def get_init_lp_agent(
    market: Market,
    target_liquidity: float,
    target_pool_apr: float,
    trade_fee_percent: float,
    seed_liquidity: float = 1,
) -> Agent:
    r"""Calculate the required deposit amounts and instantiate the LP agent

    The required deposit amounts are computed iteratively to determine market reserve levels that achieve
    the target liquidity and APR. To hit the desired ratio, the agent opens a small LP, then a short,
    then a larger LP. Each iteration estimates the slippage due to the short and adjusts the first LP amount
    to account for it. The difference in slippage from one iteration to the next monotonically decreases,
    since it is accounting for diminishing additions to the market share reserves. A more detailed description
    is here: https://github.com/element-fi/elf-simulations/pull/136#issuecomment-1405922764

    Parameters
    ----------
    market : Market
        empty market object
    target_liquidity : float
        target total liquidity for LPer to provide (bonds+shares)
        the result will be within 1e-15% of the target
    target_pool_apr : float
        target pool apr for the market
        the result will be within 1e-13% of the target
    fee_percent : float
        how much the LPer will collect in fees
    seed_liquidity : float
        initial (small) liquidity amount for setting the market APR

    Returns
    -------
    init_lp_agent : Agent
        Agent class that will perform the lp initialization action
    """
    # calc_liquidity is used to get the reserve ratio which hits the target apr
    init_share_reserves, init_bond_reserves = market.pricing_model.calc_liquidity(
        market_state=market.market_state,
        target_liquidity=seed_liquidity,  # tiny seed amount ($1)
        target_apr=target_pool_apr,
        position_duration=market.position_duration,
    )[:2]
    delta_shares = seed_liquidity
    prev_delta_shares = 0
    iteration = 0
    while abs(delta_shares - prev_delta_shares) > 1e-20 and iteration < 20:
        # estimate change in base resulting from a short
        trade_result = market.pricing_model.calc_out_given_in(
            in_=Quantity(amount=init_bond_reserves, unit=TokenType.PT),
            market_state=MarketState(
                share_reserves=init_share_reserves + delta_shares,  # estimate of first LP amount
                bond_reserves=0,
                share_price=market.market_state.share_price,
                init_share_price=market.market_state.init_share_price,
                trade_fee_percent=trade_fee_percent,
                # no redemption fee when initializing pool
                redemption_fee_percent=0,
            ),
            time_remaining=market.position_duration,
        )
        prev_delta_shares = delta_shares
        # increase first LP amount to cover slippage
        delta_shares = trade_result.user_result.d_base / market.market_state.share_price
        iteration += 1
        logging.debug(
            (
                "\niteration %g: init_share_reserves=%g delta_shares=%g"
                "\na relative change of %.2e"
                "\nestimate for first_base_lp: %g"
            ),
            iteration,
            init_share_reserves,
            delta_shares,
            (delta_shares - prev_delta_shares) / prev_delta_shares,
            (init_share_reserves + delta_shares) * market.market_state.share_price,
        )
    first_base_to_lp = (
        init_share_reserves * market.market_state.share_price + delta_shares * market.market_state.share_price
    )  # add back delta_base=delta_shares*share_price to immunize effect of short
    # TODO: investigate why max_loss_in_base is not accounted for here, as it increases the protocol liquidity,
    # even though it doesn't go into the pool.
    # see discussion: https://github.com/element-fi/elf-simulations/pull/136#discussion_r1089404750
    second_base_to_lp = (
        target_liquidity - init_share_reserves * market.market_state.share_price
    )  # fill pools to hit target liquidity
    budget = (
        first_base_to_lp
        + second_base_to_lp
        + init_bond_reserves
        - (delta_shares * market.market_state.share_price)  # delta_base
    )  # budget needs to account for max_loss, which will be deducted from the agent's wallet
    init_lp_agent = get_policy("init_lp")(  # construct the agent with desired amounts
        wallet_address=0,
        budget=budget,
        first_base_to_lp=first_base_to_lp,
        pt_to_short=init_bond_reserves,
        second_base_to_lp=second_base_to_lp,
    )
    logging.info(
        (
            "Init LP agent #%g statistics:\n\t"
            "target_apr = %g\n\t"
            "target_liquidity = %g\n\t"
            "budget = %g\n\t"
            "first_base_to_lp = %g\n\t"
            "pt_to_short = %g\n\t"
            "second_base_to_lp = %g"
        ),
        init_lp_agent.wallet.address,
        target_pool_apr,
        target_liquidity,
        budget,
        first_base_to_lp,
        init_bond_reserves,
        second_base_to_lp,
    )
    return init_lp_agent


def get_market(
    pricing_model: PricingModel,
    config: Config,
) -> Market:
    r"""Setup market

    Parameters
    ----------
    pricing_model : PricingModel
        instantiated pricing model
    config: Config
        instantiated config object. The following attributes are used:
            target_pool_apr : float
                target apr, used for calculating the time stretch
                NOTE: the market apr will not have this target value until the init_lp agent trades,
                or the share & bond reserves are explicitly set
            trade_fee_percent : float
                portion of trades to be collected as fees for LPers, expressed as a decimal
            redemption_fee_percent : float
                portion of redemptions to be collected as fees for LPers, expressed as a decimal
            num_position_days : int
                how much time between token minting and expiry, in days
            vault_apr : list
                valut apr per day for the duration of the simulation
            init_share_price : float
                the initial price of the yield bearing vault shares

    Returns
    -------
    Market
        instantiated market without any liquidity (i.e. no shares or bonds)
    """
    market = Market(
        pricing_model=pricing_model,
        market_state=MarketState(
            init_share_price=config.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=config.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
            vault_apr=config.vault_apr[0],  # yield bearing source apr
            trade_fee_percent=config.trade_fee_percent,  # g
            redemption_fee_percent=config.redemption_fee_percent,  # g
        ),
        position_duration=StretchedTime(
            days=config.num_position_days,
            time_stretch=pricing_model.calc_time_stretch(config.target_pool_apr),
            normalizing_constant=config.num_position_days,
        ),
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
    return import_module(f"elfpy.policies.{agent_type}").Policy
