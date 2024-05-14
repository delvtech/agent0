"""CRUD tests for Transaction"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest

from .interface import (
    add_checkpoint_info,
    add_pool_config,
    add_pool_infos,
    add_trade_events,
    get_all_traders,
    get_checkpoint_info,
    get_latest_block_number_from_pool_info_table,
    get_latest_block_number_from_trade_event,
    get_pool_config,
    get_pool_info,
)
from .schema import CheckpointInfo, PoolConfig, PoolInfo, TradeEvent


# These tests are using fixtures defined in conftest.py
class TestCheckpointInterface:
    """Testing postgres interface for checkpoint table"""

    @pytest.mark.docker
    def test_get_checkpoints(self, db_session):
        """Testing retrieval of checkpoints via interface"""
        checkpoint_time_1 = 100
        checkpoint_time_2 = 1000
        checkpoint_time_3 = 10000
        checkpoint_1 = CheckpointInfo(checkpoint_time=checkpoint_time_1, hyperdrive_address="a")
        checkpoint_2 = CheckpointInfo(checkpoint_time=checkpoint_time_2, hyperdrive_address="a")
        checkpoint_3 = CheckpointInfo(checkpoint_time=checkpoint_time_3, hyperdrive_address="a")
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
        checkpoint_1 = CheckpointInfo(checkpoint_time=100, hyperdrive_address="a", vault_share_price=Decimal("3.1"))
        checkpoint_2 = CheckpointInfo(checkpoint_time=1000, hyperdrive_address="a", vault_share_price=Decimal("3.2"))
        checkpoint_3 = CheckpointInfo(checkpoint_time=10000, hyperdrive_address="a", vault_share_price=Decimal("3.3"))
        add_checkpoint_info(checkpoint_1, db_session)
        add_checkpoint_info(checkpoint_2, db_session)
        add_checkpoint_info(checkpoint_3, db_session)

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=100)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [3.1])

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=1000)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [3.2])

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=10000)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [3.3])

        checkpoints_df = get_checkpoint_info(db_session, checkpoint_time=222)
        np.testing.assert_array_equal(checkpoints_df["vault_share_price"], [])

    @pytest.mark.docker
    def test_checkpoint_time_verify(self, db_session):
        """Testing querying by block number of checkpoints via interface"""
        checkpoint_1 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="a",
            vault_share_price=Decimal("3.1"),
            weighted_spot_price=Decimal("4.1"),
        )
        add_checkpoint_info(checkpoint_1, db_session)
        checkpoint_df_1 = get_checkpoint_info(db_session, hyperdrive_address="a", coerce_float=False)
        assert len(checkpoint_df_1) == 1
        assert checkpoint_df_1.loc[0, "vault_share_price"] == Decimal("3.1")
        assert checkpoint_df_1.loc[0, "weighted_spot_price"] == Decimal("4.1")

        # Nothing should happen if we give the same checkpoint info
        checkpoint_2 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="a",
            vault_share_price=Decimal("3.1"),
            weighted_spot_price=Decimal("4.1"),
        )
        add_checkpoint_info(checkpoint_2, db_session)
        checkpoint_df_2 = get_checkpoint_info(db_session, hyperdrive_address="a", coerce_float=False)
        assert len(checkpoint_df_2) == 1
        assert checkpoint_df_2.loc[0, "vault_share_price"] == Decimal("3.1")
        assert checkpoint_df_2.loc[0, "weighted_spot_price"] == Decimal("4.1")

        # Adding a checkpoint info with the same checkpoint time with a different vault share price
        # should throw a value error
        checkpoint_3 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="a",
            vault_share_price=Decimal("3.4"),
            weighted_spot_price=Decimal("4.4"),
        )
        with pytest.raises(ValueError):
            add_checkpoint_info(checkpoint_3, db_session)

        # Adding a checkpoint info with the same checkpoint time and vault share price should
        # update the other values
        checkpoint_4 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="a",
            vault_share_price=Decimal("3.1"),
            weighted_spot_price=Decimal("4.4"),
        )
        add_checkpoint_info(checkpoint_4, db_session)
        checkpoint_df_4 = get_checkpoint_info(db_session, hyperdrive_address="a", coerce_float=False)
        assert len(checkpoint_df_4) == 1
        assert checkpoint_df_4.loc[0, "vault_share_price"] == Decimal("3.1")
        assert checkpoint_df_4.loc[0, "weighted_spot_price"] == Decimal("4.4")

        # Repeat the same test with a different hyperdrive address
        # and different values
        checkpoint_1 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="b",
            vault_share_price=Decimal("5.1"),
            weighted_spot_price=Decimal("6.1"),
        )
        add_checkpoint_info(checkpoint_1, db_session)
        checkpoint_df_1 = get_checkpoint_info(db_session, hyperdrive_address="b", coerce_float=False)
        assert len(checkpoint_df_1) == 1
        assert checkpoint_df_1.loc[0, "vault_share_price"] == Decimal("5.1")
        assert checkpoint_df_1.loc[0, "weighted_spot_price"] == Decimal("6.1")

        # Nothing should happen if we give the same checkpoint info
        checkpoint_2 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="b",
            vault_share_price=Decimal("5.1"),
            weighted_spot_price=Decimal("6.1"),
        )
        add_checkpoint_info(checkpoint_2, db_session)
        checkpoint_df_2 = get_checkpoint_info(db_session, hyperdrive_address="b", coerce_float=False)
        assert len(checkpoint_df_2) == 1
        assert checkpoint_df_2.loc[0, "vault_share_price"] == Decimal("5.1")
        assert checkpoint_df_2.loc[0, "weighted_spot_price"] == Decimal("6.1")

        # Adding a checkpoint info with the same checkpoint time with a different vault share price
        # should throw a value error
        checkpoint_3 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="b",
            vault_share_price=Decimal("5.4"),
            weighted_spot_price=Decimal("6.4"),
        )
        with pytest.raises(ValueError):
            add_checkpoint_info(checkpoint_3, db_session)

        # Adding a checkpoint info with the same checkpoint time and vault share price should
        # update the other values
        checkpoint_4 = CheckpointInfo(
            checkpoint_time=100,
            hyperdrive_address="b",
            vault_share_price=Decimal("5.1"),
            weighted_spot_price=Decimal("6.4"),
        )
        add_checkpoint_info(checkpoint_4, db_session)
        checkpoint_df_4 = get_checkpoint_info(db_session, coerce_float=False)
        assert len(checkpoint_df_4) == 1
        assert checkpoint_df_4.loc[0, "vault_share_price"] == Decimal("5.1")
        assert checkpoint_df_4.loc[0, "weighted_spot_price"] == Decimal("6.4")


class TestPoolConfigInterface:
    """Testing postgres interface for poolconfig table"""

    @pytest.mark.docker
    def test_get_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)

        pool_config_df_1 = get_pool_config(db_session)
        assert len(pool_config_df_1) == 1
        np.testing.assert_array_equal(pool_config_df_1["initial_vault_share_price"], np.array([3.2]))

        pool_config_2 = PoolConfig(hyperdrive_address="1", initial_vault_share_price=Decimal("3.4"))
        add_pool_config(pool_config_2, db_session)

        pool_config_df_2 = get_pool_config(db_session)
        assert len(pool_config_df_2) == 2
        np.testing.assert_array_equal(pool_config_df_2["initial_vault_share_price"], np.array([3.2, 3.4]))

    @pytest.mark.docker
    def test_primary_id_query_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config, db_session)

        pool_config_df_1 = get_pool_config(db_session, hyperdrive_address="0")
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initial_vault_share_price"] == 3.2

        pool_config_df_2 = get_pool_config(db_session, hyperdrive_address="1")
        assert len(pool_config_df_2) == 0

    @pytest.mark.docker
    def test_pool_config_verify(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)
        pool_config_df_1 = get_pool_config(db_session)
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initial_vault_share_price"] == 3.2

        # Nothing should happen if we give the same pool_config
        pool_config_2 = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_2, db_session)
        pool_config_df_2 = get_pool_config(db_session)
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
    def test_latest_block_number(self, db_session):
        """Testing retrieval of wallet info via interface"""
        transfer_event = TradeEvent(block_number=1, hyperdrive_address="a", transaction_hash="a", wallet_address="a")
        add_trade_events([transfer_event], db_session)

        latest_block_number = get_latest_block_number_from_trade_event(db_session, "a")
        assert latest_block_number == 1

        transfer_event_1 = TradeEvent(block_number=2, hyperdrive_address="a", transaction_hash="a", wallet_address="a")
        transfer_event_2 = TradeEvent(block_number=3, hyperdrive_address="a", transaction_hash="a", wallet_address="b")
        add_trade_events([transfer_event_1, transfer_event_2], db_session)
        latest_block_number = get_latest_block_number_from_trade_event(db_session, "a")
        assert latest_block_number == 2
        latest_block_number = get_latest_block_number_from_trade_event(db_session, "b")
        assert latest_block_number == 3

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
