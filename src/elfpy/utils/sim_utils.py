from importlib import import_module
from dataclasses import dataclass, field
import logging

from elfpy.pricing_models import PricingModel, ElementPricingModel, HyperdrivePricingModel
from elfpy.markets import Market
from elfpy.agent import Agent
from elfpy.utils.config import Config
import elfpy.utils.price as price_utils
import elfpy.utils.time as time_utils


def get_init_lp_agent(
    config: Config,
    market: Market,
    pricing_model: PricingModel,
    target_liquidity: float,
    init_pool_apy: float,
    fee_percent: float,
) -> Agent:
    """
    Calculate the required deposit amounts and instantiate the LP agent

    Arguments
    ---------
    None

    Returns
    -------
    init_lp_agent : Agent
        Agent class that will perform the lp initialization action
    """
    # get the reserve amounts for the target liquidity and pool APR
    init_share_reserves, init_bond_reserves = price_utils.calc_liquidity(
        target_liquidity=target_liquidity,
        market_price=config.market.base_asset_price,
        apr=init_pool_apy,
        days_remaining=market.token_duration,
        time_stretch=market.time_stretch_constant,
        init_share_price=market.init_share_price,
        share_price=market.init_share_price,
    )[:2]
    normalized_days_until_maturity = market.token_duration  # `t(d)`; full duration
    stretch_time_remaining = time_utils.stretch_time(
        normalized_days_until_maturity, market.time_stretch_constant
    )  # tau(d)
    # mock the short to assess what the delta market conditions will be
    output_with_fee = pricing_model.calc_out_given_in(
        in_=init_bond_reserves,
        share_reserves=init_share_reserves,
        bond_reserves=0,
        token_out="pt",
        fee_percent=fee_percent,
        time_remaining=stretch_time_remaining,
        init_share_price=market.init_share_price,
        share_price=market.init_share_price,
    )[1]
    # output_with_fee will be subtracted from the share reserves, so we want to add that much extra in
    base_to_lp = init_share_reserves + output_with_fee
    # budget is the full amount for LP & short
    budget = base_to_lp + init_bond_reserves
    # construct the init_lp agent with desired budget, lp, and short amounts
    init_lp_agent = import_module("elfpy.policies.init_lp").Policy(
        wallet_address=0,
        budget=budget,
        base_to_lp=base_to_lp,
        pt_to_short=init_bond_reserves,
    )
    logging.info(
        (
            "Init LP agent #%g statistics:\ntarget_apy = %g; target_liquidity = %g; "
            "budget = %g; base_to_lp = %g; pt_to_short = %g"
        ),
        init_lp_agent.wallet_address,
        init_pool_apy,
        target_liquidity,
        budget,
        base_to_lp,
        init_bond_reserves,
    )
    return init_lp_agent


def get_pricing_model(model_name) -> ElementPricingModel | HyperdrivePricingModel:
    """
    Get a PricingModel object from the config passed in

    Arguments
    ---------

    Returns
    -------

    """
    logging.info("%s %s %s", "#" * 20, model_name, "#" * 20)
    if model_name.lower() == "hyperdrive":
        pricing_model = HyperdrivePricingModel()
    elif model_name.lower() == "element":
        pricing_model = ElementPricingModel()
    else:
        raise ValueError(f'pricing_model_name must be "HyperDrive" or "Element", not {model_name}')
    return pricing_model


def get_random_variables(config, rng):
    """
    Use random number generator to assign initial simulation parameter values

    Arguments
    ---------

    Returns
    -------

    """

    @dataclass()
    class RandomSimulationVariables:
        # dataclasses can have many attributes
        # pylint: disable=too-many-instance-attributes
        target_liquidity: float = field(metadata="total size of the market pool (bonds + shares)")
        init_pool_apy: float = field(metadata="desired fixed apy for as a decimal")
        fee_percent: float = field(metadata="percent to charge for LPer fees")
        vault_apy: list[float] = field(metadata="vault apy values")
        init_vault_age: float = field(metadata="fraction of a year since the vault was opened")
        init_share_price: float = field(default=None, metadata="initial market share price for the vault asset")

        def __post_init__(self):
            if self.init_share_price is None:
                self.init_share_price = (1 + self.vault_apy[0]) ** self.init_vault_age

    random_vars = RandomSimulationVariables(
        target_liquidity=rng.uniform(low=config.market.min_target_liquidity, high=config.market.max_target_liquidity),
        init_pool_apy=rng.uniform(
            low=config.amm.min_pool_apy, high=config.amm.max_pool_apy
        ),  # starting fixed apy as a decimal
        fee_percent=rng.uniform(low=config.amm.min_fee, high=config.amm.max_fee),
        vault_apy=list(
            rng.uniform(
                low=config.market.min_vault_apy,
                high=config.market.max_vault_apy,
                size=config.simulator.num_trading_days,
            )
        ),  # vault apy over time as a decimal
        init_vault_age=rng.uniform(low=config.market.min_vault_age, high=config.market.max_vault_age),
    )
    return random_vars
