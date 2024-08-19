"""System test for end to end usage of agent0 libraries."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fixedpointmath import FixedPoint
from utils import expect_failure_with_funded_bot, run_with_funded_bot  # type: ignore

from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy.base.errors import ContractCallException

if TYPE_CHECKING:
    from agent0.core.base import Trade
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

INVALID_SLIPPAGE = FixedPoint("-0.01")


# Build testing policy for slippage
# Simple agent, opens a set of all trades for a fixed amount and closes them after
# with a flag controlling slippage per trade
class InvalidOpenLongSlippage(HyperdriveBasePolicy):
    """Policy testing invalid slippage warnings for open longs."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Invalid open long slippage.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        elif self.counter == 1:
            action_list.append(open_long_trade(FixedPoint(22_222), INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidOpenShortSlippage(HyperdriveBasePolicy):
    """Policy testing invalid slippage warnings for open shorts."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Invalid open long short slippage.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        elif self.counter == 1:
            action_list.append(open_short_trade(FixedPoint(333), INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidRemoveLiquiditySlippage(HyperdriveBasePolicy):
    """Policy testing invalid slippage warnings for remove liquidity.
    NOTE: This policy isn't used in this test due to slippage not being implemented for remove liquidity.
    Keeping this policy here for when it does.
    """

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Invalid remove liquidity slippage.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            action_list.append(add_liquidity_trade(FixedPoint(10_000)))
        elif self.counter == 1:
            action_list.append(remove_liquidity_trade(wallet.lp_tokens, INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseLongSlippage(HyperdriveBasePolicy):
    """Policy testing invalid slippage warnings for close longs."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Invalid close long slippage.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        elif self.counter == 1:
            # Open Long
            action_list.append(open_long_trade(FixedPoint(10_000), None))
        elif self.counter == 2:
            # Closing existent long for more than I have
            assert len(wallet.longs) == 1
            for long in wallet.longs.values():
                action_list.append(close_long_trade(long.balance, long.maturity_time, INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseShortSlippage(HyperdriveBasePolicy):
    """Policy testing invalid slippage warnings for close shorts."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Invalid close short slippage.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        if self.counter == 1:
            # Open Short
            action_list.append(open_short_trade(FixedPoint(10_000), None))
        elif self.counter == 2:
            # Closing existent short for more than I have
            assert len(wallet.shorts) == 1
            for short in wallet.shorts.values():
                action_list.append(close_short_trade(short.balance, short.maturity_time, INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class TestSlippageWarning:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    @pytest.mark.docker
    def test_no_halt_on_slippage(
        self,
    ):
        chain = LocalChain(
            config=LocalChain.Config(
                chain_port=6000,
                db_port=6001,
                exception_on_policy_slippage=False,
                gas_limit=int(1e6),
            )
        )

        config = LocalHyperdrive.Config(
            initial_liquidity=FixedPoint(1_000),
            position_duration=60 * 60 * 24 * 365,  # 1 year
        )
        hyperdrive = LocalHyperdrive(chain, config)
        # All of these calls should pass if we're not halting on slippage
        run_with_funded_bot(hyperdrive, InvalidOpenLongSlippage)
        run_with_funded_bot(hyperdrive, InvalidOpenShortSlippage)
        run_with_funded_bot(hyperdrive, InvalidCloseLongSlippage)
        run_with_funded_bot(hyperdrive, InvalidCloseShortSlippage)

        chain.cleanup()

    @pytest.mark.docker
    def test_invalid_slippage_open_long(
        self,
    ):
        chain = LocalChain(
            config=LocalChain.Config(
                chain_port=6000,
                db_port=6001,
                exception_on_policy_slippage=True,
                gas_limit=int(1e6),
            )
        )
        config = LocalHyperdrive.Config(
            initial_liquidity=FixedPoint(1_000),
            position_duration=60 * 60 * 24 * 365,  # 1 year
        )
        hyperdrive = LocalHyperdrive(chain, config)
        try:
            expect_failure_with_funded_bot(hyperdrive, InvalidOpenLongSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

        chain.cleanup()

    @pytest.mark.docker
    def test_invalid_slippage_open_short(
        self,
    ):
        chain = LocalChain(
            config=LocalChain.Config(
                chain_port=6000,
                db_port=6001,
                exception_on_policy_slippage=True,
                gas_limit=int(1e6),
            )
        )
        config = LocalHyperdrive.Config(
            initial_liquidity=FixedPoint(1_000),
            position_duration=60 * 60 * 24 * 365,  # 1 year
        )
        hyperdrive = LocalHyperdrive(chain, config)
        try:
            expect_failure_with_funded_bot(hyperdrive, InvalidOpenShortSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

        chain.cleanup()

    # TODO slippage isn't implemented in the python side for add/remove liquidity and
    # withdrawal shares. Remove liquidity has bindings for slippage, but is ignored.

    @pytest.mark.docker
    def test_invalid_slippage_close_long(
        self,
    ):
        chain = LocalChain(
            config=LocalChain.Config(
                chain_port=6000,
                db_port=6001,
                exception_on_policy_slippage=True,
                gas_limit=int(1e6),
            )
        )
        config = LocalHyperdrive.Config(
            initial_liquidity=FixedPoint(1_000),
            position_duration=60 * 60 * 24 * 365,  # 1 year
        )
        hyperdrive = LocalHyperdrive(chain, config)
        try:
            expect_failure_with_funded_bot(hyperdrive, InvalidCloseLongSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

        chain.cleanup()

    @pytest.mark.docker
    def test_invalid_slippage_close_short(
        self,
    ):
        chain = LocalChain(
            config=LocalChain.Config(
                chain_port=6000,
                db_port=6001,
                exception_on_policy_slippage=True,
                gas_limit=int(1e6),
            )
        )
        config = LocalHyperdrive.Config(
            initial_liquidity=FixedPoint(1_000),
            position_duration=60 * 60 * 24 * 365,  # 1 year
        )
        hyperdrive = LocalHyperdrive(chain, config)
        try:
            expect_failure_with_funded_bot(hyperdrive, InvalidCloseShortSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

        chain.cleanup()
