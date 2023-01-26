"""Implements helper functions for setting up a simulation"""


from __future__ import annotations  # types will be strings by default in 3.11
from importlib import import_module
from typing import Any, TYPE_CHECKING, Optional
import logging

from elfpy.utils.config import Config, get_random_variables
from elfpy.simulators import Simulator
from elfpy.types import (
    MarketState,
    Quantity,
    StretchedTime,
    TokenType,
    RandomSimulationVariables,
)
from elfpy.markets import Market
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel

if TYPE_CHECKING:
    from elfpy.pricing_models.base import PricingModel
    from elfpy.agent import Agent


def get_simulator(
    config: Config, agents: Optional[list[Agent]] = None, random_sim_vars: Optional[RandomSimulationVariables] = None
) -> Simulator:
    """Constructs a simulator with sane defaults and initializes the simulator
    with an initial LP.

    Arguments
    ---------
    config : Config
        the simulator config
    agents : list[Agent]
        the agents to that should be used in the simulator
    random_sim_vars : RandomSimulationVariables
        dataclass that contains variables for initiating and running simulations
    """
    # Sample the random simulation arguments.
    if random_sim_vars is None:
        random_variables = get_random_variables(config)
    else:
        random_variables = random_sim_vars

    # Instantiate the market.
    pricing_model = get_pricing_model(config.amm.pricing_model_name)
    market = get_market(
        pricing_model,
        random_variables.target_pool_apr,
        random_variables.fee_percent,
        config.simulator.token_duration,
        random_variables.vault_apr,
        random_variables.init_share_price,
    )

    # Instantiate the initial LP agent.
    init_agents = [
        get_init_lp_agent(
            market,
            random_variables.target_liquidity,
            random_variables.target_pool_apr,
            random_variables.fee_percent,
        )
    ]

    # Initialize the simulator using only the initial LP.
    simulator = Simulator(
        config=config,
        market=market,
        random_simulation_variables=random_sim_vars,
    )
    simulator.add_agents(init_agents)
    simulator.collect_and_execute_trades()

    # Add the remaining agents.
    if not agents is None:
        simulator.add_agents(agents)

    return simulator


def get_init_lp_agent(
    market: Market,
    target_liquidity: float,
    target_pool_apr: float,
    fee_percent: float,
    init_liquidity: float = 1,
) -> Agent:
    """Calculate the required deposit amounts and instantiate the LP agent

    Arguments
    ---------
    market : Market
        empty market object
    target_liquidity : float
        target total liquidity for LPer to provide (bonds+shares)
        TODO: update this number
        the result will be within 7% of the target
    target_pool_apr : float
        target pool apr for the market
        TODO: update this number
        the result will be within 0.001 of the target
    fee_percent : float
        how much the LPer will collect in fees
    init_liquidity : float
        initial (small) liquidity amount for setting the market APR

    Returns
    -------
    init_lp_agent : Agent
        Agent class that will perform the lp initialization action
    """
    # Wrapper functions are expected to have a lot of arguments
    # pylint: disable=too-many-locals

    init_share_reserves, init_bond_reserves = market.pricing_model.calc_liquidity(
        market_state=market.market_state,
        target_liquidity=init_liquidity,
        target_apr=target_pool_apr,
        position_duration=market.position_duration,
    )[:2]
    # mock the short to assess what the delta market conditions will be
    delta_shares = 0
    delta_base = 0
    trade_result = None
    for _ in range(6):
        trade_result = market.pricing_model.calc_out_given_in(
            in_=Quantity(amount=init_bond_reserves, unit=TokenType.PT),
            market_state=MarketState(
                share_reserves=init_share_reserves + delta_shares,
                bond_reserves=0,
                share_price=market.market_state.share_price,
                init_share_price=market.market_state.init_share_price,
            ),
            fee_percent=fee_percent,
            time_remaining=market.position_duration,
        )
        delta_base = trade_result.user_result.d_base
        delta_shares = delta_base / market.market_state.share_price
    max_loss = init_bond_reserves - trade_result.user_result.d_base if trade_result is not None else 0
    init_base_reserves = init_share_reserves * market.market_state.share_price
    first_base_to_lp = init_base_reserves + delta_base  # add back delta_base to immunize effect of short
    second_base_to_lp = target_liquidity - init_base_reserves  # remember delta_base is immunized
    budget = first_base_to_lp + max_loss + second_base_to_lp  # full amount needed to trade
    init_lp_agent = import_module("elfpy.policies.init_lp").Policy(  # construct the agent with desired amounts
        wallet_address=0,
        budget=budget,
        first_base_to_lp=first_base_to_lp,
        pt_to_short=init_bond_reserves,
        second_base_to_lp=second_base_to_lp,
    )
    logging.info(
        (
            "Init LP agent #%g statistics:\n\t"
            "target_apr = %g\n\ttarget_liquidity = %g\n\t"
            "budget = %g\n\tfirst_base_to_lp = %g\n\t"
            "pt_to_short = %g\n\tsecond_base_to_lp = %g"
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
    target_pool_apr: float,
    fee_percent: float,
    position_duration: float,
    vault_apr: list,
    init_share_price: float,
) -> Market:
    """Setup market

    Arguments
    ---------
    pricing_model : PricingModel
        instantiated pricing model
    target_pool_apr : float
        target apr, used for calculating the time stretch
        NOTE: the market apr will not have this target value until the init_lp agent trades,
        or the share & bond reserves are explicitly set
    fee_percent : float
        portion of outputs to be collected as fees for LPers, expressed as a decimal
        TODO: Rename this variable so that it doesn't use "percent"
    token_duration : float
        how much time between token minting and expiry, in fractions of a year (e.g. 0.5 is 6 months)
    vault_apr : list
        valut apr per day for the duration of the simulation
    init_share_price : float
        the initial price of the yield bearing vault shares

    Returns
    -------
    Market
        instantiated market without any liquidity (i.e. no shares or bonds)

    """
    # Wrapper functions are expected to have a lot of arguments
    # pylint: disable=too-many-arguments
    market = Market(
        pricing_model=pricing_model,
        market_state=MarketState(
            init_share_price=init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
            vault_apr=vault_apr[0],  # yield bearing source apr
        ),
        position_duration=StretchedTime(
            days=position_duration * 365, time_stretch=pricing_model.calc_time_stretch(target_pool_apr)
        ),
        fee_percent=fee_percent,  # g
    )
    return market


def get_pricing_model(model_name: str) -> PricingModel:
    """Get a PricingModel object from the config passed in

    Arguments
    ---------
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


def override_random_variables(
    random_variables: RandomSimulationVariables,
    override_dict: dict[str, Any],
) -> RandomSimulationVariables:
    """Override the random simulation variables with targeted values, as specified by the keys

    Arguments
    ---------
    random_variables : RandomSimulationVariables
        dataclass that contains variables for initiating and running simulations
    override_dict : dict
        dictionary containing keys that correspond to member fields of the RandomSimulationVariables class

    Returns
    -------
    RandomSimulationVariables
        same dataclass as the random_variables input, but with fields specified by override_dict changed
    """
    allowed_keys = [
        "target_liquidity",
        "target_pool_apr",
        "fee_percent",
        "init_vault_age",
    ]
    for key, value in override_dict.items():
        if hasattr(random_variables, key):
            if key in allowed_keys:
                setattr(random_variables, key, value)
    return random_variables
