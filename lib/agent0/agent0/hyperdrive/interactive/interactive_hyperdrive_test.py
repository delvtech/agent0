"""Tests interactive hyperdrive end to end"""
import datetime
import logging
import os
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import docker
import pytest
from docker.errors import DockerException
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL
from fixedpointmath import FixedPoint

from agent0.hyperdrive.state import HyperdriveWallet

from .chain import LocalChain
from .interactive_hyperdrive import InteractiveHyperdrive


class TestInteractiveHyperdrive:
    """Tests interactive hyperdrive end to end"""

    # pylint: disable=redefined-outer-name

    @pytest.fixture(scope="function")
    def chain(self) -> Iterator[LocalChain]:
        """Creates a local chain connected to a local database hosted in docker.

        Yield
        -------
        LocalChain
            local chain instance.
        """
        # Attempt to determine if docker is installed
        try:
            try:
                _ = docker.from_env()
            except Exception:  # pylint: disable=broad-exception-caught
                home_dir = os.path.expanduser("~")
                socket_path = Path(f"{home_dir}") / ".docker" / "desktop" / "docker.sock"
                if socket_path.exists():
                    logging.debug("Docker not found at default socket, using %s..", socket_path)
                    _ = docker.DockerClient(base_url=f"unix://{socket_path}")
                else:
                    logging.debug("Docker not found.")
                    _ = docker.from_env()
        # Skip this test if docker isn't installed
        except DockerException as exc:
            # This env variable gets set when running tests in CI
            # Hence, we don't want to skip this test if we're in CI
            in_ci = os.getenv("IN_CI")
            if in_ci is None:
                pytest.skip("Docker engine not found, skipping")
            else:
                raise exc

        local_chain_config = LocalChain.Config()
        chain = LocalChain(local_chain_config)
        yield chain
        chain.cleanup()

    @pytest.mark.anvil
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
    @pytest.mark.anvil
    def test_funding_and_trades(self, chain: LocalChain):
        """Tests interactive hyperdrive end to end"""
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
        assert (FixedPoint(111) - chain_eth_balance) < FixedPoint("0.0001")
        (chain_eth_balance, chain_base_balance) = interactive_hyperdrive_2.hyperdrive_interface.get_eth_base_balances(
            hyperdrive_agent1.agent
        )
        assert chain_base_balance == FixedPoint(222222)
        # There was a little bit of gas spent to approve, so we don't do a direct comparison here
        assert (FixedPoint(222) - chain_eth_balance) < FixedPoint("0.0001")
        (chain_eth_balance, chain_base_balance) = interactive_hyperdrive.hyperdrive_interface.get_eth_base_balances(
            hyperdrive_agent2.agent
        )
        assert chain_base_balance == FixedPoint(333333)
        # There was a little bit of gas spent to approve, so we don't do a direct comparison here
        # Since we initialized without parameters, and the default is 10 eth. We then added 333 eth.
        assert (FixedPoint(343) - chain_eth_balance) < FixedPoint("0.0001")

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

    @pytest.mark.anvil
    def test_advance_time(self, chain: LocalChain):
        """Tests interactive hyperdrive end to end"""
        # We need the underlying hyperdrive interface here to test time
        interactive_hyperdrive = InteractiveHyperdrive(chain)
        hyperdrive_interface = interactive_hyperdrive.hyperdrive_interface

        current_time_1 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        # Testing passing in seconds
        chain.advance_time(3600, create_checkpoints=False)
        current_time_2 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        # Testing passing in timedelta
        chain.advance_time(datetime.timedelta(weeks=1), create_checkpoints=False)
        current_time_3 = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())

        assert current_time_2 - current_time_1 == 3600
        assert current_time_3 - current_time_2 == 3600 * 24 * 7

    @pytest.mark.anvil
    def test_advance_time_with_checkpoints(self, chain: LocalChain):
        """Tests interactive hyperdrive end to end"""
        # We need the underlying hyperdrive interface here to test time
        config = InteractiveHyperdrive.Config(checkpoint_duration=3600)
        interactive_hyperdrive = InteractiveHyperdrive(chain, config)
        hyperdrive_interface = interactive_hyperdrive.hyperdrive_interface

        # TODO there is a non-determininstic element here, the first advance time for 600 seconds
        # may push the time forward past a checkpoint boundary depending on the current time,
        # in which case 1 checkpoint will be made. Hence, we can't be certain on how many checkpoints
        # were made per advance time.

        # Advance time lower than a checkpoint duration
        pre_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        checkpoint_events = chain.advance_time(600, create_checkpoints=True)
        post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        assert post_time - pre_time == 600
        # assert 0 or 1 checkpoints made
        assert len(checkpoint_events[interactive_hyperdrive]) in [0, 1]

        # Advance time equal to a checkpoint duration
        pre_time = post_time
        checkpoint_events = chain.advance_time(3600, create_checkpoints=True)
        post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        # Advancing time equal to checkpoint duration results in time being off by few second
        assert abs(post_time - pre_time - 3600) <= 2
        # assert one checkpoint made
        assert len(checkpoint_events[interactive_hyperdrive]) in [1, 2]

        # Advance time with multiple checkpoints
        pre_time = post_time
        checkpoint_events = chain.advance_time(datetime.timedelta(hours=3), create_checkpoints=True)
        post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        # Advancing time equal to checkpoint duration results in time being off by few second
        assert abs(post_time - pre_time - 3600 * 3) <= 2
        # assert 3 checkpoints made
        assert len(checkpoint_events[interactive_hyperdrive]) in [3, 4]

        ## Checking when advancing time of a value not a multiple of checkpoint_duration ##
        pre_time = post_time
        # Advance time with multiple checkpoints
        checkpoint_events = chain.advance_time(4000, create_checkpoints=True)
        post_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_current_block())
        # Advancing time equal to checkpoint duration results in time being off by few second
        assert abs(post_time - pre_time - 4000) <= 2
        # assert 1 checkpoint made
        assert len(checkpoint_events[interactive_hyperdrive]) in [1, 2]

        # TODO add additional columns in data pipeline for checkpoints from CreateCheckpoint event
        # then check `hyperdrive_interface.get_checkpoint_info` for proper checkpoints.

    @pytest.mark.anvil
    def test_save_load_snapshot(self, chain: LocalChain):
        # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
        initial_pool_config = InteractiveHyperdrive.Config()
        interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)
        hyperdrive_interface = interactive_hyperdrive.hyperdrive_interface

        # Generate funded trading agents from the interactive object
        # Make trades to set the initial state
        hyperdrive_agent = interactive_hyperdrive.init_agent(base=FixedPoint(111111), eth=FixedPoint(111), name="alice")
        open_long_event = hyperdrive_agent.open_long(base=FixedPoint(2222))
        open_short_event = hyperdrive_agent.open_short(bonds=FixedPoint(3333))
        hyperdrive_agent.add_liquidity(base=FixedPoint(4444))

        # Save the state on the chain
        chain.save_snapshot()

        # To ensure snapshots are working, we check the agent's wallet on the chain, the wallet object in the agent,
        # and in the db
        # Check base balance on the chain
        init_eth_on_chain, init_base_on_chain = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
        init_agent_wallet = hyperdrive_agent.wallet.copy()
        init_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False).copy()
        init_pool_info_on_chain = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state().pool_info
        init_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

        # Make a few trades to change the state
        hyperdrive_agent.close_long(bonds=FixedPoint(222), maturity_time=open_long_event.maturity_time)
        hyperdrive_agent.open_short(bonds=FixedPoint(333))
        hyperdrive_agent.remove_liquidity(shares=FixedPoint(444))

        # Ensure state has changed
        check_eth_on_chain, check_base_on_chain = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
        check_agent_wallet = hyperdrive_agent.wallet
        check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
        check_pool_info_on_chain = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state().pool_info
        check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

        assert check_eth_on_chain != init_eth_on_chain
        assert check_base_on_chain != init_base_on_chain
        assert check_agent_wallet != init_agent_wallet
        assert not check_db_wallet.equals(init_db_wallet)
        assert check_pool_info_on_chain != init_pool_info_on_chain
        assert not check_pool_state_on_db.equals(init_pool_state_on_db)

        # Save snapshot and check for equality
        chain.load_snapshot()

        check_eth_on_chain, check_base_on_chain = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
        check_agent_wallet = hyperdrive_agent.wallet
        check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
        check_pool_info_on_chain = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state().pool_info
        check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

        assert check_eth_on_chain == init_eth_on_chain
        assert check_base_on_chain == init_base_on_chain
        assert check_agent_wallet == init_agent_wallet
        assert check_db_wallet.equals(init_db_wallet)
        assert check_pool_info_on_chain == init_pool_info_on_chain
        assert check_pool_state_on_db.equals(init_pool_state_on_db)

        # Do it again to make sure we can do multiple loads

        # Make a few trades to change the state
        hyperdrive_agent.open_long(base=FixedPoint(222))
        hyperdrive_agent.close_short(bonds=FixedPoint(333), maturity_time=open_short_event.maturity_time)
        hyperdrive_agent.remove_liquidity(shares=FixedPoint(555))

        # Ensure state has changed
        check_eth_on_chain, check_base_on_chain = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
        check_agent_wallet = hyperdrive_agent.wallet
        check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
        check_pool_info_on_chain = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state().pool_info
        check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

        assert check_eth_on_chain != init_eth_on_chain
        assert check_base_on_chain != init_base_on_chain
        assert check_agent_wallet != init_agent_wallet
        assert not check_db_wallet.equals(init_db_wallet)
        assert check_pool_info_on_chain != init_pool_info_on_chain
        assert not check_pool_state_on_db.equals(init_pool_state_on_db)

        # Save snapshot and check for equality
        chain.load_snapshot()

        check_eth_on_chain, check_base_on_chain = hyperdrive_interface.get_eth_base_balances(hyperdrive_agent.agent)
        check_agent_wallet = hyperdrive_agent.wallet
        check_db_wallet = interactive_hyperdrive.get_current_wallet(coerce_float=False)
        check_pool_info_on_chain = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state().pool_info
        check_pool_state_on_db = interactive_hyperdrive.get_pool_state(coerce_float=False)

        assert check_eth_on_chain == init_eth_on_chain
        assert check_base_on_chain == init_base_on_chain
        assert check_agent_wallet == init_agent_wallet
        assert check_db_wallet.equals(init_db_wallet)
        assert check_pool_info_on_chain == init_pool_info_on_chain
        assert check_pool_state_on_db.equals(init_pool_state_on_db)

    @pytest.mark.anvil
    def test_set_variable_rate(self, chain: LocalChain):
        # We need the underlying hyperdrive interface here to test time
        config = InteractiveHyperdrive.Config(initial_variable_rate=FixedPoint("0.05"))
        interactive_hyperdrive = InteractiveHyperdrive(chain, config)

        # Make a trade to mine the block on this variable rate so it shows up in the data pipeline
        _ = interactive_hyperdrive.init_agent()

        # Set the variable rate
        # This mines a block since it's a transaction
        interactive_hyperdrive.set_variable_rate(FixedPoint("0.10"))

        # Ensure variable rate has changed
        pool_state_df = interactive_hyperdrive.get_pool_state(coerce_float=False)

        assert pool_state_df["variable_rate"].iloc[0] == Decimal("0.05")
        assert pool_state_df["variable_rate"].iloc[-1] == Decimal("0.10")

    @pytest.mark.anvil
    def test_access_deployer_account(self, chain: LocalChain):
        config = InteractiveHyperdrive.Config(
            initial_liquidity=FixedPoint("100"),
        )
        interactive_hyperdrive = InteractiveHyperdrive(chain, config)
        privkey = chain.get_deployer_account_private_key()  # anvil account 0
        pubkey = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
        larry = interactive_hyperdrive.init_agent(base=FixedPoint(100_000), name="larry", private_key=privkey)
        assert larry.wallet.address.hex().startswith(pubkey.lower())  # deployer public key

    @pytest.mark.anvil
    def test_remove_deployer_liquidity(self, chain: LocalChain):
        config = InteractiveHyperdrive.Config(
            initial_liquidity=FixedPoint(100),
        )
        interactive_hyperdrive = InteractiveHyperdrive(chain, config)
        privkey = chain.get_deployer_account_private_key()  # anvil account 0
        larry = interactive_hyperdrive.init_agent(base=FixedPoint(100_000), name="larry", private_key=privkey)
        # Ideally this would hold the accurate number of LP tokens, but the amount from initialization isn't
        # included in acquire_data. Instead, we hack some coins into his wallet, to avoid error checks.
        larry.wallet.lp_tokens = FixedPoint(100)
        # I don't know how many shares he actually has, so I'm guessing here.
        larry.remove_liquidity(shares=FixedPoint(5))
