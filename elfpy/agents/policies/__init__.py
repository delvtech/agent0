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

    BASE_POLICY = BasePolicy
    INITIALIZE_LIQUIDITY_AGENT = InitializeLiquidityAgent
    LP_AND_WITHDRAW_AGENT = LpAndWithdrawAgent
    NO_ACTION_POLICY = NoActionPolicy
    RANDOM_AGENT = RandomAgent
    SINGLE_LONG_AGENT = SingleLongAgent
    SINGLE_LP_AGENT = SingleLpAgent
    SINGLE_SHORT_AGENT = SingleShortAgent
    LONG_LOUIE = LongLouie
    SHORT_SALLY = ShortSally
