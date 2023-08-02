"""Policies for expert system trading bots"""
from typing import NamedTuple

from .base import BasePolicy
from .init_lp import InitializeLiquidityAgent
from .lp_and_withdraw import LpAndWithdrawAgent
from .no_action import NoActionPolicy
from .random_agent import RandomAgent
from .single_long import SingleLongAgent
from .single_lp import SingleLpAgent
from .single_short import SingleShortAgent
from .smart_long import LongLouie
from .smart_short import ShortSally


class Policies(NamedTuple):
    """All policies in elfpy."""

    base_policy = BasePolicy
    initialize_liquidity_agent = InitializeLiquidityAgent
    lp_and_withdraw_agent = LpAndWithdrawAgent
    no_action_policy = NoActionPolicy
    random_agent = RandomAgent
    single_long_agent = SingleLongAgent
    single_lp_agent = SingleLpAgent
    single_short_agent = SingleShortAgent
    long_louie = LongLouie
    short_sally = ShortSally
