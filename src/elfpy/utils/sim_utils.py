"""Implements helper functions for setting up a simulation"""


from __future__ import annotations  # types will be strings by default in 3.11
from importlib import import_module
from typing import Any, Callable, TYPE_CHECKING
import logging

from stochastic.processes import GeometricBrownianMotion

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
        the result will be within 7% of the target
    target_pool_apr : float
        target pool apr for the market
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
    # pylint: disable=too-many-arguments
    # get the reserve amounts for a small target liquidity to achieve a target pool APR
    init_share_reserves, init_bond_reserves = market.pricing_model.calc_liquidity(
        market_state=market.market_state,
        target_liquidity=init_liquidity,
        target_apr=target_pool_apr,
        position_duration=market.position_duration,
    )[:2]
    # mock the short to assess what the delta market conditions will be
    output_with_fee = market.pricing_model.calc_out_given_in(
        in_=Quantity(amount=init_bond_reserves, unit=TokenType.BASE),
        market_state=MarketState(
            share_reserves=init_share_reserves,
            bond_reserves=0,
            share_price=market.market_state.init_share_price,
            init_share_price=market.market_state.init_share_price,
        ),
        fee_percent=fee_percent,
        time_remaining=market.position_duration,
    ).breakdown.with_fee
    # output_with_fee will be subtracted from the share reserves, so we want to add that much extra in
    first_base_to_lp = init_share_reserves + output_with_fee
    short_amount = init_bond_reserves
    second_base_to_lp = target_liquidity - init_share_reserves
    # budget is the full amount for LP & short
    budget = first_base_to_lp + short_amount + second_base_to_lp
    # construct the init_lp agent with desired budget, lp, and short amounts
    init_lp_agent = import_module("elfpy.policies.init_lp").Policy(
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


def setup_vault_apr(config, rng):
    """Construct the vault_apr list
    Note: callable type option would allow for infinite num_trading_days after small modifications

    Arguments
    ---------
    config : Config
        config object, as defined in elfpy.utils.config
    rng : Generator
        random number generator; output of np.random.default_rng(seed)

    Returns
    -------
    vault_apr : list
        list of apr values that is the same length as num_trading_days
    """
    if isinstance(config.market.vault_apr, dict):  # dictionary specifies parameters for the callable
        allowable_keys = ["constant", "uniform", "geometricbrownianmotion"]
        if config.market.vault_apr["type"].lower() in allowable_keys:
            match config.market.vault_apr["type"].lower():
                case "constant":
                    vault_apr = [
                        config.market.vault_apr["value"],
                    ] * config.simulator.num_trading_days
                case "uniform":
                    vault_apr = rng.uniform(
                        low=config.market.vault_apr["low"],
                        high=config.market.vault_apr["high"],
                        size=config.simulator.num_trading_days,
                    ).tolist()
                case "geometricbrownianmotion":
                    # the n argument is number of steps, so the number of points is n+1
                    vault_apr = (
                        GeometricBrownianMotion(rng=rng)
                        .sample(n=config.simulator.num_trading_days - 1, initial=config.market.vault_apr["initial"])
                        .tolist()
                    )
        else:
            raise ValueError(f"{config.market.vault_apr['type']=} not in {allowable_keys=}")
    elif isinstance(config.market.vault_apr, Callable):  # callable function
        vault_apr = [config.market.vault_apr() for _ in range(config.simulator.num_trading_days)]
    elif isinstance(config.market.vault_apr, list):  # user-defined list of values
        vault_apr = config.market.vault_apr
    else:
        raise TypeError(
            f"config.market.vault_apr must be a list, dict, or callable, not {type(config.market.vault_apr)}"
        )
    return vault_apr


def get_random_variables(config, rng):
    """Use random number generator to assign initial simulation parameter values

    Arguments
    ---------
    config : Config
        config object, as defined in elfpy.utils.config
    rng : Generator
        random number generator; output of np.random.default_rng(seed)

    Returns
    -------
    RandomSimulationVariables
        dataclass that contains variables for initiating and running simulations
    """
    random_vars = RandomSimulationVariables(
        target_liquidity=rng.uniform(low=config.market.min_target_liquidity, high=config.market.max_target_liquidity),
        target_pool_apr=rng.uniform(
            low=config.amm.min_pool_apr, high=config.amm.max_pool_apr
        ),  # starting fixed apr as a decimal
        fee_percent=rng.uniform(low=config.amm.min_fee, high=config.amm.max_fee),
        vault_apr=setup_vault_apr(config, rng),
        init_vault_age=rng.uniform(low=config.market.min_vault_age, high=config.market.max_vault_age),
    )
    return random_vars


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


def override_config_variables(config, override_dict):
    """Replace existing member & config variables with ones defined in override_dict

    Arguments
    ---------
    config : Config
        config object, as defined in elfpy.utils.config
    override_dict : dict
        dictionary containing keys that correspond to member fields of the RandomSimulationVariables class

    Returns
    -------
    Config
        same dataclass as the config input, but with fields specified by override_dict changed
    """
    # override the config variables, including random variables that were set
    for key, value in override_dict.items():
        for variable_object in [config.market, config.amm, config.simulator]:
            if hasattr(
                variable_object, key
            ):  # TODO: This is a non safe HACK -- we should assign & type each key/value individually
                logging.debug("Overridding %s from %s to %s.", key, str(getattr(variable_object, key)), str(value))
                setattr(variable_object, key, value)
    return config
