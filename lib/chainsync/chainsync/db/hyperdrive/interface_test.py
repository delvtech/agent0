"""CRUD tests for Transaction"""
from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest
from chainsync.db.base import get_latest_block_number_from_table
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL

from .interface import (
    add_checkpoint_infos,
    add_current_wallet,
    add_pool_config,
    add_pool_infos,
    add_transactions,
    add_wallet_deltas,
    get_all_traders,
    get_checkpoint_info,
    get_current_wallet,
    get_latest_block_number_from_pool_info_table,
    get_latest_block_number_from_table,
    get_pool_config,
    get_pool_info,
    get_transactions,
    get_wallet_deltas,
)
from .schema import CheckpointInfo, CurrentWallet, HyperdriveTransaction, PoolConfig, PoolInfo, WalletDelta


# These tests are using fixtures defined in conftest.py
class TestTransactionInterface:
    """Testing postgres interface for transaction table"""

    def test_latest_block_number(self, db_session):
        """Testing retrieval of transaction via interface"""
        transaction_1 = HyperdriveTransaction(blockNumber=1, transactionHash="a", event_value=Decimal("3.0"))
        add_transactions([transaction_1], db_session)

        latest_block_number = get_latest_block_number_from_table(HyperdriveTransaction, db_session)
        assert latest_block_number == 1

        transaction_2 = HyperdriveTransaction(blockNumber=2, transactionHash="b", event_value=Decimal("3.2"))
        transaction_3 = HyperdriveTransaction(blockNumber=3, transactionHash="c", event_value=Decimal("3.4"))
        add_transactions([transaction_2, transaction_3], db_session)

        latest_block_number = get_latest_block_number_from_table(HyperdriveTransaction, db_session)
        assert latest_block_number == 3

    def test_get_transactions(self, db_session):
        """Testing retrieval of transactions via interface"""
        transaction_1 = HyperdriveTransaction(blockNumber=0, transactionHash="a", event_value=Decimal("3.1"))
        transaction_2 = HyperdriveTransaction(blockNumber=1, transactionHash="b", event_value=Decimal("3.2"))
        transaction_3 = HyperdriveTransaction(blockNumber=2, transactionHash="c", event_value=Decimal("3.3"))
        add_transactions([transaction_1, transaction_2, transaction_3], db_session)

        transactions_df = get_transactions(db_session)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.1, 3.2, 3.3])

    def test_block_query_transactions(self, db_session):
        """Testing querying by block number of transactions via interface"""
        transaction_1 = HyperdriveTransaction(blockNumber=0, transactionHash="a", event_value=Decimal("3.1"))
        transaction_2 = HyperdriveTransaction(blockNumber=1, transactionHash="b", event_value=Decimal("3.2"))
        transaction_3 = HyperdriveTransaction(blockNumber=2, transactionHash="c", event_value=Decimal("3.3"))
        add_transactions([transaction_1, transaction_2, transaction_3], db_session)

        transactions_df = get_transactions(db_session, start_block=1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.2, 3.3])

        transactions_df = get_transactions(db_session, start_block=-1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.3])

        transactions_df = get_transactions(db_session, end_block=1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.1])

        transactions_df = get_transactions(db_session, end_block=-1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.1, 3.2])

        transactions_df = get_transactions(db_session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.2])


class TestCheckpointInterface:
    """Testing postgres interface for checkpoint table"""

    def test_latest_block_number(self, db_session):
        """Testing retrieval of checkpoint via interface"""
        checkpoint_1 = CheckpointInfo(blockNumber=1, timestamp=datetime.now())
        add_checkpoint_infos([checkpoint_1], db_session)
        db_session.commit()

        latest_block_number = get_latest_block_number_from_table(CheckpointInfo, db_session)
        assert latest_block_number == 1

        checkpoint_2 = CheckpointInfo(blockNumber=2, timestamp=datetime.now())
        checkpoint_3 = CheckpointInfo(blockNumber=3, timestamp=datetime.now())
        add_checkpoint_infos([checkpoint_2, checkpoint_3], db_session)

        latest_block_number = get_latest_block_number_from_table(CheckpointInfo, db_session)
        assert latest_block_number == 3

    def test_get_checkpoints(self, db_session):
        """Testing retrieval of checkpoints via interface"""
        date_1 = datetime(1945, 8, 6)
        date_2 = datetime(1984, 8, 9)
        date_3 = datetime(2001, 9, 11)
        checkpoint_1 = CheckpointInfo(blockNumber=0, timestamp=date_1)
        checkpoint_2 = CheckpointInfo(blockNumber=1, timestamp=date_2)
        checkpoint_3 = CheckpointInfo(blockNumber=2, timestamp=date_3)
        add_checkpoint_infos([checkpoint_1, checkpoint_2, checkpoint_3], db_session)

        checkpoints_df = get_checkpoint_info(db_session)
        np.testing.assert_array_equal(
            checkpoints_df["timestamp"].dt.to_pydatetime(), np.array([date_1, date_2, date_3])
        )

    def test_block_query_checkpoints(self, db_session):
        """Testing querying by block number of checkpoints via interface"""
        checkpoint_1 = CheckpointInfo(blockNumber=0, timestamp=datetime.now(), sharePrice=Decimal("3.1"))
        checkpoint_2 = CheckpointInfo(blockNumber=1, timestamp=datetime.now(), sharePrice=Decimal("3.2"))
        checkpoint_3 = CheckpointInfo(blockNumber=2, timestamp=datetime.now(), sharePrice=Decimal("3.3"))
        add_checkpoint_infos([checkpoint_1, checkpoint_2, checkpoint_3], db_session)

        checkpoints_df = get_checkpoint_info(db_session, start_block=1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.2, 3.3])

        checkpoints_df = get_checkpoint_info(db_session, start_block=-1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.3])

        checkpoints_df = get_checkpoint_info(db_session, end_block=1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.1])

        checkpoints_df = get_checkpoint_info(db_session, end_block=-1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.1, 3.2])

        checkpoints_df = get_checkpoint_info(db_session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.2])


class TestPoolConfigInterface:
    """Testing postgres interface for poolconfig table"""

    def test_get_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)

        pool_config_df_1 = get_pool_config(db_session)
        assert len(pool_config_df_1) == 1
        np.testing.assert_array_equal(pool_config_df_1["initialSharePrice"], np.array([3.2]))

        pool_config_2 = PoolConfig(contractAddress="1", initialSharePrice=Decimal("3.4"))
        add_pool_config(pool_config_2, db_session)

        pool_config_df_2 = get_pool_config(db_session)
        assert len(pool_config_df_2) == 2
        np.testing.assert_array_equal(pool_config_df_2["initialSharePrice"], np.array([3.2, 3.4]))

    def test_primary_id_query_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        add_pool_config(pool_config, db_session)

        pool_config_df_1 = get_pool_config(db_session, contract_address="0")
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initialSharePrice"] == 3.2

        pool_config_df_2 = get_pool_config(db_session, contract_address="1")
        assert len(pool_config_df_2) == 0

    def test_pool_config_verify(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)
        pool_config_df_1 = get_pool_config(db_session)
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initialSharePrice"] == 3.2

        # Nothing should happen if we give the same pool_config
        pool_config_2 = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        add_pool_config(pool_config_2, db_session)
        pool_config_df_2 = get_pool_config(db_session)
        assert len(pool_config_df_2) == 1
        assert pool_config_df_2.loc[0, "initialSharePrice"] == 3.2

        # If we try to add another pool config with a different value, should throw a ValueError
        pool_config_3 = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.4"))
        with pytest.raises(ValueError):
            add_pool_config(pool_config_3, db_session)


class TestPoolInfoInterface:
    """Testing postgres interface for poolinfo table"""

    def test_latest_block_number(self, db_session):
        """Testing latest block number call"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(blockNumber=1, timestamp=timestamp_1)
        add_pool_infos([pool_info_1], db_session)

        latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
        assert latest_block_number == 1

        timestamp_1 = datetime.fromtimestamp(1628472002)
        pool_info_1 = PoolInfo(blockNumber=2, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472004)
        pool_info_2 = PoolInfo(blockNumber=3, timestamp=timestamp_2)
        add_pool_infos([pool_info_1, pool_info_2], db_session)

        latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
        assert latest_block_number == 3

    def test_get_pool_info(self, db_session):
        """Testing retrieval of pool info via interface"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(blockNumber=0, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(blockNumber=1, timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(blockNumber=2, timestamp=timestamp_3)
        add_pool_infos([pool_info_1, pool_info_2, pool_info_3], db_session)

        pool_info_df = get_pool_info(db_session)
        np.testing.assert_array_equal(
            pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_1, timestamp_2, timestamp_3])
        )

    def test_block_query_pool_info(self, db_session):
        """Testing retrieval of pool info via interface"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(blockNumber=0, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(blockNumber=1, timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(blockNumber=2, timestamp=timestamp_3)
        add_pool_infos([pool_info_1, pool_info_2, pool_info_3], db_session)
        pool_info_df = get_pool_info(db_session, start_block=1)
        np.testing.assert_array_equal(
            pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_2, timestamp_3])
        )
        pool_info_df = get_pool_info(db_session, start_block=-1)
        np.testing.assert_array_equal(pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_3]))
        pool_info_df = get_pool_info(db_session, end_block=1)
        np.testing.assert_array_equal(pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_1]))
        pool_info_df = get_pool_info(db_session, end_block=-1)
        np.testing.assert_array_equal(
            pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_1, timestamp_2])
        )
        pool_info_df = get_pool_info(db_session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_2]))


class TestWalletDeltaInterface:
    """Testing postgres interface for walletinfo table"""

    def test_latest_block_number(self, db_session):
        """Testing retrieval of wallet info via interface"""
        wallet_delta_1 = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.0"))
        add_wallet_deltas([wallet_delta_1], db_session)
        latest_block_number = get_latest_block_number_from_table(WalletDelta, db_session)
        assert latest_block_number == 1
        wallet_delta_2 = WalletDelta(blockNumber=2, transactionHash="a", delta=Decimal("3.2"))
        wallet_delta_3 = WalletDelta(blockNumber=3, transactionHash="a", delta=Decimal("3.4"))
        add_wallet_deltas([wallet_delta_2, wallet_delta_3], db_session)
        latest_block_number = get_latest_block_number_from_table(WalletDelta, db_session)
        assert latest_block_number == 3

    def test_get_wallet_delta(self, db_session):
        """Testing retrievals of walletinfo via interface"""
        wallet_delta_1 = WalletDelta(blockNumber=0, transactionHash="a", delta=Decimal("3.1"))
        wallet_delta_2 = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        wallet_delta_3 = WalletDelta(blockNumber=2, transactionHash="a", delta=Decimal("3.3"))
        add_wallet_deltas([wallet_delta_1, wallet_delta_2, wallet_delta_3], db_session)
        wallet_delta_df = get_wallet_deltas(db_session)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.1, 3.2, 3.3]))

    def test_block_query_wallet_delta(self, db_session):
        """Testing querying by block number of wallet info via interface"""
        wallet_delta_1 = WalletDelta(blockNumber=0, transactionHash="a", delta=Decimal("3.1"))
        wallet_delta_2 = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        wallet_delta_3 = WalletDelta(blockNumber=2, transactionHash="a", delta=Decimal("3.3"))
        add_wallet_deltas([wallet_delta_1, wallet_delta_2, wallet_delta_3], db_session)
        wallet_delta_df = get_wallet_deltas(db_session, start_block=1)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.2, 3.3]))
        wallet_delta_df = get_wallet_deltas(db_session, start_block=-1)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.3]))
        wallet_delta_df = get_wallet_deltas(db_session, end_block=1)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.1]))
        wallet_delta_df = get_wallet_deltas(db_session, end_block=-1)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.1, 3.2]))
        wallet_delta_df = get_wallet_deltas(db_session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.2]))

    def test_get_agents(self, db_session):
        """Testing helper function to get current wallet values"""
        wallet_delta_1 = WalletDelta(blockNumber=0, transactionHash="a", walletAddress="addr_1")
        wallet_delta_2 = WalletDelta(blockNumber=1, transactionHash="b", walletAddress="addr_1")
        wallet_delta_3 = WalletDelta(blockNumber=2, transactionHash="c", walletAddress="addr_2")
        add_wallet_deltas([wallet_delta_1, wallet_delta_2, wallet_delta_3], db_session)
        agents = get_all_traders(db_session).to_list()
        assert len(agents) == 2
        assert "addr_1" in agents
        assert "addr_2" in agents


class TestCurrentWalletInterface:
    """Testing postgres interface for CurrentWallet table"""

    def test_latest_block_number(self, db_session):
        """Testing retrieval of wallet info via interface"""
        wallet_info_1 = CurrentWallet(blockNumber=1, value=Decimal("3.0"))
        add_current_wallet([wallet_info_1], db_session)
        latest_block_number = get_latest_block_number_from_table(CurrentWallet, db_session)
        assert latest_block_number == 1
        wallet_info_2 = CurrentWallet(blockNumber=2, value=Decimal("3.2"))
        wallet_info_3 = CurrentWallet(blockNumber=3, value=Decimal("3.4"))
        add_current_wallet([wallet_info_2, wallet_info_3], db_session)
        latest_block_number = get_latest_block_number_from_table(CurrentWallet, db_session)
        assert latest_block_number == 3

    def test_get_current_wallet(self, db_session):
        """Testing retrieval of walletinfo via interface"""
        wallet_info_1 = CurrentWallet(blockNumber=0, walletAddress="a", value=Decimal("3.1"))
        wallet_info_2 = CurrentWallet(blockNumber=1, walletAddress="b", value=Decimal("3.2"))
        wallet_info_3 = CurrentWallet(blockNumber=2, walletAddress="c", value=Decimal("3.3"))
        add_current_wallet([wallet_info_1, wallet_info_2, wallet_info_3], db_session)
        wallet_info_df = get_current_wallet(db_session)
        np.testing.assert_array_equal(wallet_info_df["value"], np.array([3.1, 3.2, 3.3]))

    def test_block_query_wallet_info(self, db_session):
        """Testing querying by block number of wallet info via interface"""
        wallet_info_1 = CurrentWallet(blockNumber=0, walletAddress="a", value=Decimal("3.1"))
        wallet_info_2 = CurrentWallet(blockNumber=1, walletAddress="b", value=Decimal("3.2"))
        wallet_info_3 = CurrentWallet(blockNumber=2, walletAddress="c", value=Decimal("3.3"))
        add_current_wallet([wallet_info_1, wallet_info_2, wallet_info_3], db_session)
        wallet_info_df = get_current_wallet(db_session, end_block=1)
        np.testing.assert_array_equal(wallet_info_df["value"], np.array([3.1]))
        wallet_info_df = get_current_wallet(db_session, end_block=-1)
        np.testing.assert_array_equal(wallet_info_df["value"], np.array([3.1, 3.2]))

    def test_current_wallet_info(self, db_session):
        """Testing helper function to get current wallet values"""
        wallet_info_1 = CurrentWallet(
            blockNumber=0, walletAddress="addr", tokenType=BASE_TOKEN_SYMBOL, value=Decimal("3.1")
        )
        wallet_info_2 = CurrentWallet(blockNumber=1, walletAddress="addr", tokenType="LP", value=Decimal("5.1"))
        add_current_wallet([wallet_info_1, wallet_info_2], db_session)
        wallet_info_df = get_current_wallet(db_session).reset_index()
        np.testing.assert_array_equal(wallet_info_df["tokenType"], [BASE_TOKEN_SYMBOL, "LP"])
        np.testing.assert_array_equal(wallet_info_df["value"], [3.1, 5.1])
        # E.g., block 2, wallet base tokens gets updated to 6.1
        wallet_info_3 = CurrentWallet(
            blockNumber=2, walletAddress="addr", tokenType=BASE_TOKEN_SYMBOL, value=Decimal("6.1")
        )
        add_current_wallet([wallet_info_3], db_session)
        wallet_info_df = get_current_wallet(db_session).reset_index()
        np.testing.assert_array_equal(wallet_info_df["tokenType"], [BASE_TOKEN_SYMBOL, "LP"])
        np.testing.assert_array_equal(wallet_info_df["value"], [6.1, 5.1])
