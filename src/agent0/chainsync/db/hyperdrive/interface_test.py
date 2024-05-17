"""CRUD tests for Transaction"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest

from .interface import (
    add_checkpoint_info,
    add_hyperdrive_addr_to_name,
    add_pool_config,
    add_pool_infos,
    add_trade_events,
    get_all_traders,
    get_checkpoint_info,
    get_hyperdrive_addr_to_name,
    get_latest_block_number_from_pool_info_table,
    get_latest_block_number_from_trade_event,
    get_pool_config,
    get_pool_info,
)
from .schema import CheckpointInfo, PoolConfig, PoolInfo, TradeEvent


class TestHyperdriveAddrToName:
    """Testing postgres interface for usermap table"""

    @pytest.mark.docker
    def test_get_addr_to_username(self, db_session):
        """Testing retrieval of usernames via interface"""
        name_1 = "a"
        address_1 = "1"
        add_hyperdrive_addr_to_name(name=name_1, hyperdrive_address=address_1, session=db_session)
        name_2 = "b"
        address_2 = "2"
        add_hyperdrive_addr_to_name(name=name_2, hyperdrive_address=address_2, session=db_session)
        name_3 = "c"
        address_3 = "3"
        add_hyperdrive_addr_to_name(name=name_3, hyperdrive_address=address_3, session=db_session)

        map_df = get_hyperdrive_addr_to_name(db_session)
        assert len(map_df) == 3
        # Sort by usernames, then address to ensure order
        map_df = map_df.sort_values(["name", "hyperdrive_address"], axis=0)
        np.testing.assert_array_equal(map_df["name"], ["a", "b", "c"])
        np.testing.assert_array_equal(map_df["hyperdrive_address"], ["1", "2", "3"])

    @pytest.mark.docker
    def test_get_query_address(self, db_session):
        """Testing querying by address of addr_to_username via interface"""
        name_1 = "a"
        address_1 = "1"
        add_hyperdrive_addr_to_name(name=name_1, hyperdrive_address=address_1, session=db_session)
        name_2 = "b"
        address_2 = "2"
        add_hyperdrive_addr_to_name(name=name_2, hyperdrive_address=address_2, session=db_session)
        name_3 = "c"
        address_3 = "3"
        add_hyperdrive_addr_to_name(name=name_3, hyperdrive_address=address_3, session=db_session)

        user_map_df = get_hyperdrive_addr_to_name(db_session, hyperdrive_address="1")
        np.testing.assert_array_equal(user_map_df["name"], ["a"])
        user_map_df = get_hyperdrive_addr_to_name(db_session, hyperdrive_address="2")
        np.testing.assert_array_equal(user_map_df["name"], ["b"])
        user_map_df = get_hyperdrive_addr_to_name(db_session, hyperdrive_address="3")
        np.testing.assert_array_equal(user_map_df["name"], ["c"])

    @pytest.mark.docker
    def test_addr_to_username_insertion_error(self, db_session):
        """Testing insertion conflicts of addr_to_username via interface"""
        name_1 = "a"
        address_1 = "1"
        add_hyperdrive_addr_to_name(name=name_1, hyperdrive_address=address_1, session=db_session)

        # Adding the same addresses with the same username should pass
        name_2 = "a"
        address_2 = "1"
        add_hyperdrive_addr_to_name(name=name_2, hyperdrive_address=address_2, session=db_session)

        map_df = get_hyperdrive_addr_to_name(db_session)
        assert len(map_df) == 1

        # Sort by usernames, then address to ensure order
        map_df = map_df.sort_values(["name", "hyperdrive_address"], axis=0)
        np.testing.assert_array_equal(map_df["name"], ["a"])
        np.testing.assert_array_equal(map_df["hyperdrive_address"], ["1"])

        # Adding the same addresses with different username should fail
        # The add_addr_to_username is all or nothing, so if one fails, all fails
        name_3 = "b"
        address_3 = "1"
        with pytest.raises(ValueError):
            add_hyperdrive_addr_to_name(name=name_3, hyperdrive_address=address_3, session=db_session)

        # Final db values shouldn't change
        map_df = get_hyperdrive_addr_to_name(db_session)
        assert len(map_df) == 1
        # Sort by usernames, then address to ensure order
        map_df = map_df.sort_values(["name", "hyperdrive_address"], axis=0)
        np.testing.assert_array_equal(map_df["name"], ["a"])
        np.testing.assert_array_equal(map_df["hyperdrive_address"], ["1"])

    @pytest.mark.docker
    def test_addr_to_username_force_insertion(self, db_session):
        """Testing force insertion of addr_to_username via interface"""
        name_1 = "a"
        address_1 = "1"
        add_hyperdrive_addr_to_name(name=name_1, hyperdrive_address=address_1, session=db_session)

        # Force update
        name_2 = "b"
        address_2 = "1"
        add_hyperdrive_addr_to_name(name=name_2, hyperdrive_address=address_2, session=db_session, force_update=True)

        map_df = get_hyperdrive_addr_to_name(db_session)
        assert len(map_df) == 1

        # Sort by usernames, then address to ensure order
        map_df = map_df.sort_values(["name", "hyperdrive_address"], axis=0)
        np.testing.assert_array_equal(map_df["name"], ["b"])
        np.testing.assert_array_equal(map_df["hyperdrive_address"], ["1"])


# These tests are using fixtures defined in conftest.py
class TestCheckpointInterface:
    """Testing postgres interface for checkpoint table"""

    @pytest.mark.docker
    def test_get_checkpoints(self, db_session):
        """Testing retrieval of checkpoints via interface"""
        checkpoint_time_1 = 100
        checkpoint_time_2 = 1000
        checkpoint_time_3 = 10000
        checkpoint_1 = CheckpointInfo(checkpoint_time=checkpoint_time_1, hyperdrive_address="a", block_number=1)
        checkpoint_2 = CheckpointInfo(checkpoint_time=checkpoint_time_2, hyperdrive_address="a", block_number=2)
        checkpoint_3 = CheckpointInfo(checkpoint_time=checkpoint_time_3, hyperdrive_address="a", block_number=3)
        add_checkpoint_info(checkpoint_1, db_session)
        add_checkpoint_info(checkpoint_2, db_session)
        add_checkpoint_info(checkpoint_3, db_session)

        checkpoints_df = get_checkpoint_info(db_session)
        np.testing.assert_array_equal(
            np.array(checkpoints_df["checkpoint_time"].values),
            np.array([checkpoint_time_1, checkpoint_time_2, checkpoint_time_3]),
        )

    @pytest.mark.docker
    def test_checkpoint_time_query_checkpoints(self, db_session):
        """Testing querying by block number of checkpoints via interface"""
        checkpoint_1 = CheckpointInfo(
            checkpoint_time=100, hyperdrive_address="a", block_number=1, vault_share_price=Decimal("3.1")
        )
        checkpoint_2 = CheckpointInfo(
            checkpoint_time=1000, hyperdrive_address="a", block_number=2, vault_share_price=Decimal("3.2")
        )
        checkpoint_3 = CheckpointInfo(
            checkpoint_time=10000, hyperdrive_address="a", block_number=3, vault_share_price=Decimal("3.3")
        )
        add_checkpoint_info(checkpoint_1, db_session)
        add_checkpoint_info(checkpoint_2, db_session)
        add_checkpoint_info(checkpoint_3, db_session)

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=100, coerce_float=True)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [3.1])

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=1000, coerce_float=True)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [3.2])

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=10000, coerce_float=True)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [3.3])

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=222, coerce_float=True)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [])


class TestPoolConfigInterface:
    """Testing postgres interface for poolconfig table"""

    @pytest.mark.docker
    def test_get_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)

        pool_config_df_1 = get_pool_config(db_session, coerce_float=True)
        assert len(pool_config_df_1) == 1
        np.testing.assert_array_equal(pool_config_df_1["initial_vault_share_price"], np.array([3.2]))

        pool_config_2 = PoolConfig(hyperdrive_address="1", initial_vault_share_price=Decimal("3.4"))
        add_pool_config(pool_config_2, db_session)

        pool_config_df_2 = get_pool_config(db_session, coerce_float=True)
        assert len(pool_config_df_2) == 2
        np.testing.assert_array_equal(pool_config_df_2["initial_vault_share_price"], np.array([3.2, 3.4]))

    @pytest.mark.docker
    def test_primary_id_query_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config, db_session)

        pool_config_df_1 = get_pool_config(db_session, hyperdrive_address="0", coerce_float=True)
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initial_vault_share_price"] == 3.2

        pool_config_df_2 = get_pool_config(db_session, hyperdrive_address="1", coerce_float=True)
        assert len(pool_config_df_2) == 0

    @pytest.mark.docker
    def test_pool_config_verify(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)
        pool_config_df_1 = get_pool_config(db_session, coerce_float=True)
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initial_vault_share_price"] == 3.2

        # Nothing should happen if we give the same pool_config
        pool_config_2 = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_2, db_session)
        pool_config_df_2 = get_pool_config(db_session, coerce_float=True)
        assert len(pool_config_df_2) == 1
        assert pool_config_df_2.loc[0, "initial_vault_share_price"] == 3.2

        # If we try to add another pool config with a different value, should throw a ValueError
        pool_config_3 = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.4"))
        with pytest.raises(ValueError):
            add_pool_config(pool_config_3, db_session)


class TestPoolInfoInterface:
    """Testing postgres interface for poolinfo table"""

    @pytest.mark.docker
    def test_latest_block_number(self, db_session):
        """Testing latest block number call"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(block_number=1, hyperdrive_address="a", timestamp=timestamp_1)
        add_pool_infos([pool_info_1], db_session)

        latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
        assert latest_block_number == 1

        timestamp_1 = datetime.fromtimestamp(1628472002)
        pool_info_1 = PoolInfo(block_number=2, hyperdrive_address="a", timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472004)
        pool_info_2 = PoolInfo(block_number=3, hyperdrive_address="a", timestamp=timestamp_2)
        add_pool_infos([pool_info_1, pool_info_2], db_session)

        latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
        assert latest_block_number == 3

    @pytest.mark.docker
    def test_get_pool_info(self, db_session):
        """Testing retrieval of pool info via interface"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(block_number=0, hyperdrive_address="a", timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(block_number=1, hyperdrive_address="a", timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(block_number=2, hyperdrive_address="a", timestamp=timestamp_3)
        add_pool_infos([pool_info_1, pool_info_2, pool_info_3], db_session)

        pool_info_df = get_pool_info(db_session)
        np.testing.assert_array_equal(
            np.array(pool_info_df["timestamp"].values),
            np.array([timestamp_1, timestamp_2, timestamp_3]).astype("datetime64[ns]"),
        )

    @pytest.mark.docker
    def test_block_query_pool_info(self, db_session):
        """Testing retrieval of pool info via interface"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(block_number=0, hyperdrive_address="a", timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(block_number=1, hyperdrive_address="a", timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(block_number=2, hyperdrive_address="a", timestamp=timestamp_3)
        add_pool_infos([pool_info_1, pool_info_2, pool_info_3], db_session)
        pool_info_df = get_pool_info(db_session, start_block=1)
        np.testing.assert_array_equal(
            np.array(pool_info_df["timestamp"].values), np.array([timestamp_2, timestamp_3]).astype("datetime64[ns]")
        )
        pool_info_df = get_pool_info(db_session, start_block=-1)
        np.testing.assert_array_equal(
            np.array(pool_info_df["timestamp"].values), np.array([timestamp_3]).astype("datetime64[ns]")
        )
        pool_info_df = get_pool_info(db_session, end_block=1)
        np.testing.assert_array_equal(
            np.array(pool_info_df["timestamp"].values), np.array([timestamp_1]).astype("datetime64[ns]")
        )
        pool_info_df = get_pool_info(db_session, end_block=-1)
        np.testing.assert_array_equal(
            np.array(pool_info_df["timestamp"].values), np.array([timestamp_1, timestamp_2]).astype("datetime64[ns]")
        )
        pool_info_df = get_pool_info(db_session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(
            np.array(pool_info_df["timestamp"].values), np.array([timestamp_2]).astype("datetime64[ns]")
        )


class TestHyperdriveEventsInterface:
    """Testing postgres interface for walletinfo table"""

    @pytest.mark.docker
    def test_latest_block_number_on_wallet(self, db_session):
        """Testing retrieval of wallet info via interface"""
        transfer_event = TradeEvent(block_number=1, transaction_hash="a", hyperdrive_address="a", wallet_address="1")
        add_trade_events([transfer_event], db_session)

        latest_block_number = get_latest_block_number_from_trade_event(
            db_session, hyperdrive_address=None, wallet_address="1"
        )
        assert latest_block_number == 1

        transfer_event_1 = TradeEvent(block_number=2, transaction_hash="a", hyperdrive_address="a", wallet_address="1")
        transfer_event_2 = TradeEvent(block_number=1, transaction_hash="a", hyperdrive_address="a", wallet_address="2")
        add_trade_events([transfer_event_1, transfer_event_2], db_session)
        latest_block_number = get_latest_block_number_from_trade_event(
            db_session, hyperdrive_address=None, wallet_address="1"
        )
        assert latest_block_number == 2
        latest_block_number = get_latest_block_number_from_trade_event(
            db_session, hyperdrive_address=None, wallet_address="2"
        )
        assert latest_block_number == 1

    @pytest.mark.docker
    def test_latest_block_number_on_hyperdrive_address(self, db_session):
        """Testing retrieval of wallet info via interface"""
        transfer_event = TradeEvent(block_number=1, transaction_hash="a", hyperdrive_address="a", wallet_address="1")
        add_trade_events([transfer_event], db_session)

        latest_block_number = get_latest_block_number_from_trade_event(
            db_session, hyperdrive_address="a", wallet_address=None
        )
        assert latest_block_number == 1

        transfer_event_1 = TradeEvent(block_number=2, transaction_hash="a", hyperdrive_address="a", wallet_address="1")
        transfer_event_2 = TradeEvent(block_number=1, transaction_hash="a", hyperdrive_address="b", wallet_address="1")
        add_trade_events([transfer_event_1, transfer_event_2], db_session)
        latest_block_number = get_latest_block_number_from_trade_event(
            db_session, hyperdrive_address="a", wallet_address=None
        )
        assert latest_block_number == 2
        latest_block_number = get_latest_block_number_from_trade_event(
            db_session, hyperdrive_address="b", wallet_address=None
        )
        assert latest_block_number == 1

    @pytest.mark.docker
    def test_get_agents(self, db_session):
        """Testing helper function to get current wallet values"""
        wallet_delta_1 = TradeEvent(
            block_number=0, hyperdrive_address="a", transaction_hash="a", wallet_address="addr_1"
        )
        wallet_delta_2 = TradeEvent(
            block_number=1, hyperdrive_address="a", transaction_hash="b", wallet_address="addr_1"
        )
        wallet_delta_3 = TradeEvent(
            block_number=2, hyperdrive_address="a", transaction_hash="c", wallet_address="addr_2"
        )
        add_trade_events([wallet_delta_1, wallet_delta_2, wallet_delta_3], db_session)
        agents = get_all_traders(db_session).to_list()
        assert len(agents) == 2
        assert "addr_1" in agents
        assert "addr_2" in agents
