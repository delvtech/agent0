"""Close long market trade tests that match those being executed in the solidity repo"""
import unittest
from decimal import getcontext
import inspect

import pytest

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types


# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


@pytest.fixture(scope="class")
def hyperdrive_mock():
    """Test object"""
    return HyperdriveMock()


class HyperdriveMock(unittest.TestCase):
    """Mocks a Hyperdrive market"""

    contribution: float = 500_000_000
    target_apr: float = 0.05
    term_length: int = 365
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_market.Market

    def __init__(self):
        """Set up agent, pricing model, & market for the subsequent tests"""
        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        block_time = time.BlockTime()
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.MarketState(
            trade_fee_percent=0.0,
            redemption_fee_percent=0.0,
        )
        self.hyperdrive = hyperdrive_market.Market(
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTime(
                days=365, time_stretch=pricing_model.calc_time_stretch(self.target_apr), normalizing_constant=365
            ),
            block_time=block_time,
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, 0.05)
        self.alice.wallet.update(wallet_deltas)


def verify_slippage(self, base_output, base_input, precision, func):
    self.assertLess(  # user gets less than what they put in
        base_output,
        base_input,
        msg=f"{func}(precision={precision:.0f}) has no slippage",
    )


precision = range(18, 27)


def func():
    """Return function name"""
    return inspect.stack()[1].function


def idfn(val):
    # note this wouldn't show any hours/minutes/seconds
    return f"precision={val:.0f}"


@pytest.mark.parametrize("precision", precision, ids=idfn)
def test_precision_long_open(precision):
    """Make sure we have slippage on a long open"""
    hyperdrive = hyperdrive_mock()
    getcontext().prec = precision
    base_amount = 10
    hyperdrive.bob.budget = base_amount
    hyperdrive.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
    _, agent_deltas_open = hyperdrive.hyperdrive.open_long(
        agent_wallet=hyperdrive.bob.wallet,
        base_amount=base_amount,
    )
    verify_slippage(hyperdrive, agent_deltas_open.balance.amount, base_amount, precision, func())


@pytest.mark.parametrize("precision", precision, ids=idfn)
def test_precision_long_close(precision):
    """Make sure we have slippage on a long open and close round trip"""
    hyperdrive = hyperdrive_mock()
    getcontext().prec = precision
    base_amount = 10
    hyperdrive.bob.budget = base_amount
    hyperdrive.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
    _, agent_deltas_open = hyperdrive.hyperdrive.open_long(
        agent_wallet=hyperdrive.bob.wallet,
        base_amount=base_amount,
    )
    _, agent_deltas_close = hyperdrive.hyperdrive.close_long(
        agent_wallet=hyperdrive.bob.wallet,
        bond_amount=agent_deltas_open.longs[0].balance,
        mint_time=0,
    )
    verify_slippage(hyperdrive, agent_deltas_close.balance.amount, base_amount, precision, func())


@pytest.mark.parametrize("precision", precision, ids=idfn)
def test_precision_short_open(precision):
    """Make sure we have slippage on a short open"""
    hyperdrive = hyperdrive_mock()
    getcontext().prec = precision
    trade_amount = 10  # this will be reflected in BASE in the wallet and PTs in the short
    hyperdrive.bob.budget = trade_amount
    hyperdrive.bob.wallet.balance = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
    base_paid_without_slippage = (1 - hyperdrive.hyperdrive.spot_price) * trade_amount
    _, agent_deltas_open = hyperdrive.hyperdrive.open_short(
        agent_wallet=hyperdrive.bob.wallet,
        bond_amount=trade_amount,
    )
    base_paid = agent_deltas_open.balance.amount
    verify_slippage(hyperdrive, base_paid, base_paid_without_slippage, precision, func())


@pytest.mark.parametrize("precision", precision, ids=idfn)
def test_precision_short_close(precision):
    """Make sure we have slippage on a short open and close round trip"""
    hyperdrive = hyperdrive_mock()
    getcontext().prec = precision
    trade_amount = 10  # this will be reflected in BASE in the wallet and PTs in the short
    hyperdrive.bob.budget = trade_amount
    hyperdrive.bob.wallet.balance = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
    base_paid_without_slippage = (1 - hyperdrive.hyperdrive.spot_price) * trade_amount
    _, agent_deltas_open = hyperdrive.hyperdrive.open_short(
        agent_wallet=hyperdrive.bob.wallet,
        bond_amount=trade_amount,
    )
    base_paid = abs(agent_deltas_open.balance.amount)
    hyperdrive.assertLess(
        base_paid_without_slippage,
        base_paid,  # should pay more with slippage
    )
    _, agent_deltas_close = hyperdrive.hyperdrive.close_short(
        agent_wallet=hyperdrive.bob.wallet,
        bond_amount=agent_deltas_open.shorts[0].balance,
        mint_time=0,
        open_share_price=1,
    )
    base_received = agent_deltas_close.balance.amount
    verify_slippage(hyperdrive, base_received, base_paid, precision, func())
