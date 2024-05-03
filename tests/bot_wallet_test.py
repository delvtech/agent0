"""System test for checking calculated wallets versus wallets on chain."""

from __future__ import annotations

import pytest
from fixedpointmath import FixedPoint
from utils import run_with_funded_bot

from agent0.core.base import Trade
from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.interactive import LocalHyperdrive
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy.hyperdrive import AssetIdPrefix, HyperdriveReadInterface, encode_asset_id


def ensure_agent_wallet_is_correct(wallet: HyperdriveWallet, interface: HyperdriveReadInterface) -> None:
    """Check that the agent's wallet matches what's reported from the chain.

    Will assert that balances match.

    Arguments
    ---------
    wallet: HyperdriveWallet
        The HyperdriveWallet object to check against the chain
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object
    """
    # Check base
    base_from_chain = interface.base_token_contract.functions.balanceOf(
        interface.web3.to_checksum_address(wallet.address.hex())
    ).call()
    assert wallet.balance.amount == FixedPoint(scaled_value=base_from_chain)

    # Check lp positions
    asset_id = encode_asset_id(AssetIdPrefix.LP, 0)
    address = interface.web3.to_checksum_address(wallet.address.hex())
    lp_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
    assert wallet.lp_tokens == FixedPoint(scaled_value=lp_from_chain)

    # Check withdrawal positions
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    address = interface.web3.to_checksum_address(wallet.address.hex())
    withdrawal_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
    assert wallet.withdraw_shares == FixedPoint(scaled_value=withdrawal_from_chain)

    # Check long positions
    for long_time, long_amount in wallet.longs.items():
        asset_id = encode_asset_id(AssetIdPrefix.LONG, long_time)
        address = interface.web3.to_checksum_address(wallet.address.hex())
        long_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
        assert long_amount.balance == FixedPoint(scaled_value=long_from_chain)

    # Check short positions
    for short_time, short_amount in wallet.shorts.items():
        asset_id = encode_asset_id(AssetIdPrefix.SHORT, short_time)
        address = interface.web3.to_checksum_address(wallet.address.hex())
        short_from_chain = interface.hyperdrive_contract.functions.balanceOf(asset_id, address).call()
        assert short_amount.balance == FixedPoint(scaled_value=short_from_chain)


class WalletTestAgainstChainPolicy(HyperdriveBasePolicy):
    """An agent that simply cycles through all trades."""

    COUNTER_ADD_LIQUIDITY = 0
    COUNTER_OPEN_LONG = 1
    COUNTER_OPEN_SHORT = 2
    COUNTER_REMOVE_LIQUIDITY = 3
    COUNTER_CLOSE_LONGS = 4
    COUNTER_CLOSE_SHORTS = 5
    COUNTER_REDEEM_WITHDRAW_SHARES = 6
    COUNTER_CHECK = 7

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Open all trades for a fixed amount and closes them after, one at a time.

        After each trade, the agent will ensure the wallet passed in matches what's on the chain.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market.
        wallet: HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False

        if self.counter == self.COUNTER_ADD_LIQUIDITY:
            # Add liquidity
            action_list.append(add_liquidity_trade(trade_amount=FixedPoint(111_111)))
        elif self.counter == self.COUNTER_OPEN_LONG:
            # Open Long
            action_list.append(open_long_trade(FixedPoint(22_222), self.slippage_tolerance))
        elif self.counter == self.COUNTER_OPEN_SHORT:
            # Open Short
            action_list.append(open_short_trade(FixedPoint(333), self.slippage_tolerance))
        elif self.counter == self.COUNTER_REMOVE_LIQUIDITY:
            # Remove All Liquidity
            action_list.append(remove_liquidity_trade(wallet.lp_tokens))
        elif self.counter == self.COUNTER_CLOSE_LONGS:
            # Close All Longs
            assert len(wallet.longs) == 1
            for long_time, long in wallet.longs.items():
                action_list.append(close_long_trade(long.balance, long_time, self.slippage_tolerance))
        elif self.counter == self.COUNTER_CLOSE_SHORTS:
            # Close All Shorts
            assert len(wallet.shorts) == 1
            for short_time, short in wallet.shorts.items():
                action_list.append(close_short_trade(short.balance, short_time, self.slippage_tolerance))
        elif self.counter == self.COUNTER_REDEEM_WITHDRAW_SHARES:
            # Redeem all withdrawal shares
            action_list.append(redeem_withdraw_shares_trade(wallet.withdraw_shares))
        elif self.counter == self.COUNTER_CHECK:
            # One final check after the previous trade
            pass
        else:
            done_trading = True

        # After each trade, check the wallet for correctness against the chain
        ensure_agent_wallet_is_correct(wallet, interface)
        self.counter += 1
        return action_list, done_trading


class TestWalletAgainstChain:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    @pytest.mark.anvil
    def test_wallet_against_chain(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        """Runs the entire pipeline and checks the database at the end. All arguments are fixtures."""

        run_with_funded_bot(fast_hyperdrive_fixture, WalletTestAgainstChainPolicy)
