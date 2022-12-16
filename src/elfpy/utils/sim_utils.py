"""Implements helper functions for setting up a simulation"""
from importlib import import_module
from dataclasses import dataclass, field
import logging
from typing import Any

from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.element import ElementPricingModel
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel
from elfpy.markets import Market
from elfpy.agent import Agent
from elfpy.types import MarketState, Quantity, StretchedTime, TokenType
from elfpy.utils.config import Config
import elfpy.utils.price as price_utils


@dataclass()
class RandomSimulationVariables:
    """Random variables to be used during simulation setup & execution"""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    target_liquidity: float = field(metadata="total size of the market pool (bonds + shares)")
    target_pool_apy: float = field(metadata="desired fixed apy for as a decimal")
    fee_percent: float = field(metadata="percent to charge for LPer fees")
    vault_apy: list[float] = field(metadata="vault apy values")
    init_vault_age: float = field(metadata="fraction of a year since the vault was opened")
    init_share_price: float = field(default=None, metadata="initial market share price for the vault asset")

    def __post_init__(self):
        """init_share_price is a function of other random variables"""
        if self.init_share_price is None:
            self.init_share_price = (1 + self.vault_apy[0]) ** self.init_vault_age


def get_init_lp_agent(
    config: Config,
    market: Market,
    pricing_model: PricingModel,
    target_liquidity: float,
    target_pool_apy: float,
    fee_percent: float,
    init_liquidity: float = 1,
) -> Agent:
    """
    Calculate the required deposit amounts and instantiate the LP agent

    Arguments
    ---------
    config : Config
        config object, as defined in elfpy.utils.config
    market : Market
        empty market object
    pricing_model : PricingModel
        desired pricing model
    target_liquidity : float
        target total liquidity for LPer to provide (bonds+shares)
        the result will be within 7% of the target
    target_pool_apy : float
        target pool apy for the market
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
    init_share_reserves, init_bond_reserves = price_utils.calc_liquidity(
        target_liquidity=init_liquidity,
        market_price=config.market.base_asset_price,
        apr=target_pool_apy,
        time_remaining=market.position_duration,
        init_share_price=market.market_state.init_share_price,
        share_price=market.market_state.init_share_price,
    )[:2]
    # mock the short to assess what the delta market conditions will be
    output_with_fee = pricing_model.calc_out_given_in(
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
            "target_apy = %g\n\ttarget_liquidity = %g\n\t"
            "budget = %g\n\tfirst_base_to_lp = %g\n\t"
            "pt_to_short = %g\n\tsecond_base_to_lp = %g"
        ),
        init_lp_agent.wallet_address,
        target_pool_apy,
        target_liquidity,
        budget,
        first_base_to_lp,
        init_bond_reserves,
        second_base_to_lp,
    )
    return init_lp_agent


def get_market(
    pricing_model: PricingModel,
    target_pool_apy: float,
    fee_percent: float,
    position_duration: float,
    init_share_price: float,
) -> Market:
    """Setup market

    Arguments
    ---------
    pricing_model : PricingModel
        instantiated pricing model
    target_pool_apy : float
        target apy, used for calculating the time stretch
        NOTE: the market apy will not have this target value until the init_lp agent trades,
        or the share & bond reserves are explicitly set
    fee_percent : float
        portion of outputs to be collected as fees for LPers, expressed as a decimal
        TODO: Rename this variable so that it doesn't use "percent"
    token_duration : float
        how much time between token minting and expiry, in fractions of a year (e.g. 0.5 is 6 months)
    init_share_price : float
        the initial price of the yield bearing vault shares

    Returns
    -------
    Market
        instantiated market without any liquidity (i.e. no shares or bonds)

    """
    market = Market(
        market_state=MarketState(
            init_share_price=init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
        ),
        position_duration=StretchedTime(
            days=position_duration * 365, time_stretch=pricing_model.calc_time_stretch(target_pool_apy)
        ),
        fee_percent=fee_percent,  # g
    )
    return market


def get_pricing_model(model_name: str) -> PricingModel:
    """Get a PricingModel object from the config passed in

    Arguments
    ---------
    model_name : str
        name of the desired pricing_model; can be "element", "hyperdrive", or "yieldspace"

    Returns
    -------
    PricingModel
        instantiated pricing model matching the input argument
    """
    logging.info("%s %s %s", "#" * 20, model_name, "#" * 20)
    if model_name.lower() == "element":
        pricing_model = ElementPricingModel()
    elif model_name.lower() == "hyperdrive":
        pricing_model = HyperdrivePricingModel()
    elif model_name.lower() == "yieldspace":
        pricing_model = YieldSpacePricingModel()
    else:
        raise ValueError(f'pricing_model_name must be "Element", "Hyperdrive", or "YieldSpace", not {model_name}')
    return pricing_model


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
        target_pool_apy=rng.uniform(
            low=config.amm.min_pool_apy, high=config.amm.max_pool_apy
        ),  # starting fixed apy as a decimal
        fee_percent=rng.uniform(low=config.amm.min_fee, high=config.amm.max_fee),
        vault_apy=rng.uniform(
            low=config.market.min_vault_apy,
            high=config.market.max_vault_apy,
            size=config.simulator.num_trading_days,
        ).tolist(),  # vault apy over time as a decimal
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

    vault_apy: list[float] = field(metadata="vault apy values")
    """
    allowed_keys = [
        "target_liquidity",
        "target_pool_apy",
        "fee_percent",
        "init_vault_age",
        "init_share_price",
        "vault_apy",
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
