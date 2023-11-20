"""Tests interactive hyperdrive end to end"""
import datetime

from ethpy.hyperdrive import BASE_TOKEN_SYMBOL
from fixedpointmath import FixedPoint

from agent0.hyperdrive.state import HyperdriveWallet

from .chain import LocalChain
from .interactive_hyperdrive import InteractiveHyperdrive


class TestInteractiveHyperdrive:
    """Tests interactive hyperdrive end to end"""

    def _ensure_db_wallet_matches_agent_wallet(
        self,
        interactive_hyperdrive: InteractiveHyperdrive,
        agent_wallet: HyperdriveWallet,
    ):
        # NOTE this function is assuming only one agent is making trades

        # Test against db
        current_wallet_df = interactive_hyperdrive.get_current_wallet(coerce_float=False)

        base_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == BASE_TOKEN_SYMBOL]
        assert len(base_wallet_df) == 1
        assert agent_wallet.balance.amount == FixedPoint(base_wallet_df.iloc[0]["position"])

        # Check lp
        lp_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "LP"]
        if len(lp_wallet_df) == 0:
            check_value = FixedPoint(0)
        elif len(lp_wallet_df) == 1:
            check_value = FixedPoint(lp_wallet_df.iloc[0]["position"])
        else:
            assert False
        assert check_value == agent_wallet.lp_tokens

        # Check longs
        long_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "LONG"]
        assert len(long_wallet_df) == len(agent_wallet.longs)
        for _, long_df in long_wallet_df.iterrows():
            assert long_df["maturity_time"] in agent_wallet.longs
            assert agent_wallet.longs[long_df["maturity_time"]].balance == long_df["position"]

        # Check shorts
        short_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "SHORT"]
        assert len(short_wallet_df) == len(agent_wallet.shorts)
        for _, short_df in short_wallet_df.iterrows():
            assert short_df["maturity_time"] in agent_wallet.shorts
            assert agent_wallet.shorts[short_df["maturity_time"]].balance == short_df["position"]

        # Check withdrawal_shares
        withdrawal_wallet_df = current_wallet_df[current_wallet_df["base_token_type"] == "WITHDRAWAL_SHARE"]
        if len(withdrawal_wallet_df) == 0:
            check_value = FixedPoint(0)
        elif len(withdrawal_wallet_df) == 1:
            check_value = FixedPoint(withdrawal_wallet_df.iloc[0]["position"])
        else:
            assert False
        assert check_value == agent_wallet.withdraw_shares

    # Lots of things to test
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    def test_funding_and_trades(self):
        """Tests interactive hyperdrive end to end"""
        # Construct chain object
        local_chain_config = LocalChain.Config()
        chain = LocalChain(local_chain_config)

        # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
        initial_pool_config = InteractiveHyperdrive.Config()
        # Launches 2 pools on the same local chain
        interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)
        interactive_hyperdrive_2 = InteractiveHyperdrive(chain, initial_pool_config)

        # Generate funded trading agents from the interactive object
        # Names are reflected on output data frames and plots later
        hyperdrive_agent0 = interactive_hyperdrive.init_agent(
            base=FixedPoint(111111), eth=FixedPoint(111), name="alice"
        )
        hyperdrive_agent1 = interactive_hyperdrive_2.init_agent(
            base=FixedPoint(222222), eth=FixedPoint(222), name="bob"
        )
        # Omission of name defaults to wallet address
        hyperdrive_agent2 = interactive_hyperdrive.init_agent()

        # Add funds to an agent
        hyperdrive_agent2.add_funds(base=FixedPoint(333333), eth=FixedPoint(333))

        # Ensure agent wallet have expected balances
        assert (hyperdrive_agent0.wallet.balance.amount) == FixedPoint(111111)
        assert (hyperdrive_agent1.wallet.balance.amount) == FixedPoint(222222)
        assert (hyperdrive_agent2.wallet.balance.amount) == FixedPoint(333333)
        # Ensure chain balances are as expected
        (chain_eth_balance, chain_base_balance) = interactive_hyperdrive.hyperdrive_interface.get_eth_base_balances(
            hyperdrive_agent0.agent
        )
        assert chain_base_balance == FixedPoint(111111)
        # There was a little bit of gas spent to approve, so we don't do a direct comparison here
        assert (FixedPoint(111) - chain_eth_balance) < FixedPoint("0.001")
        (chain_eth_balance, chain_base_balance) = interactive_hyperdrive_2.hyperdrive_interface.get_eth_base_balances(
            hyperdrive_agent1.agent
        )
        assert chain_base_balance == FixedPoint(222222)
        # There was a little bit of gas spent to approve, so we don't do a direct comparison here
        assert (FixedPoint(222) - chain_eth_balance) < FixedPoint("0.001")
        (chain_eth_balance, chain_base_balance) = interactive_hyperdrive.hyperdrive_interface.get_eth_base_balances(
            hyperdrive_agent2.agent
        )
        assert chain_base_balance == FixedPoint(333333)
        # There was a little bit of gas spent to approve, so we don't do a direct comparison here
        assert (FixedPoint(333) - chain_eth_balance) < FixedPoint("0.001")

        # Test trades
        # Add liquidity
        add_liquidity_event = hyperdrive_agent0.add_liquidity(base=FixedPoint(1111))
        assert add_liquidity_event.base_amount == FixedPoint(1111)
        assert hyperdrive_agent0.wallet.lp_tokens == add_liquidity_event.lp_amount
        self._ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

        # Open long
        open_long_event = hyperdrive_agent0.open_long(base=FixedPoint(2222))
        assert open_long_event.base_amount == FixedPoint(2222)
        agent0_longs = list(hyperdrive_agent0.wallet.longs.values())
        assert len(agent0_longs) == 1
        assert agent0_longs[0].balance == open_long_event.bond_amount
        assert agent0_longs[0].maturity_time == open_long_event.maturity_time
        self._ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

        # Open short
        open_short_event = hyperdrive_agent0.open_short(bonds=FixedPoint(3333))
        assert open_short_event.bond_amount == FixedPoint(3333)
        agent0_shorts = list(hyperdrive_agent0.wallet.shorts.values())
        assert len(agent0_shorts) == 1
        assert agent0_shorts[0].balance == open_short_event.bond_amount
        assert agent0_shorts[0].maturity_time == open_short_event.maturity_time
        self._ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

        # Remove liquidity
        remove_liquidity_event = hyperdrive_agent0.remove_liquidity(shares=add_liquidity_event.lp_amount)
        assert add_liquidity_event.lp_amount == remove_liquidity_event.lp_amount
        assert hyperdrive_agent0.wallet.lp_tokens == FixedPoint(0)
        assert hyperdrive_agent0.wallet.withdraw_shares == remove_liquidity_event.withdrawal_share_amount
        self._ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

        # Close long
        close_long_event = hyperdrive_agent0.close_long(
            maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
        )
        assert open_long_event.bond_amount == close_long_event.bond_amount
        assert open_long_event.maturity_time == close_long_event.maturity_time
        assert len(hyperdrive_agent0.wallet.longs) == 0
        self._ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

        # Close short
        close_short_event = hyperdrive_agent0.close_short(
            maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
        )
        assert open_short_event.bond_amount == close_short_event.bond_amount
        assert open_short_event.maturity_time == close_short_event.maturity_time
        assert len(hyperdrive_agent0.wallet.shorts) == 0
        self._ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

        # Redeem withdrawal shares
        redeem_event = hyperdrive_agent0.redeem_withdraw_share(shares=remove_liquidity_event.withdrawal_share_amount)
        assert redeem_event.withdrawal_share_amount == remove_liquidity_event.withdrawal_share_amount
        assert hyperdrive_agent0.wallet.withdraw_shares == FixedPoint(0)
        self._ensure_db_wallet_matches_agent_wallet(interactive_hyperdrive, hyperdrive_agent0.wallet)

    def test_advance_time(self):
        """Tests interactive hyperdrive end to end"""
        # Construct chain object
        local_chain_config = LocalChain.Config()
        chain = LocalChain(local_chain_config)
        # We need the underlying hyperdrive interface here to test time
        interactive_hyperdrive = InteractiveHyperdrive(chain)
        hyperdrive_interface = interactive_hyperdrive.hyperdrive_interface

        current_time_1 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        # Testing passing in seconds
        chain.advance_time(3600)
        current_time_2 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        # Testing passing in timedelta
        chain.advance_time(datetime.timedelta(weeks=1))
        current_time_3 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())

        assert current_time_2 - current_time_1 == 3600
        assert current_time_3 - current_time_2 == 3600 * 24 * 7