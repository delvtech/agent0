"""CRUD tests for Transaction"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest

from agent0.chainsync.db.base import get_latest_block_number_from_table
from agent0.ethpy.hyperdrive import BASE_TOKEN_SYMBOL

from .interface import (
    add_checkpoint_info,
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

    @pytest.mark.docker
    def test_latest_block_number(self, db_session):
        """Testing retrieval of transaction via interface"""
        transaction_1 = HyperdriveTransaction(block_number=1, transaction_hash="a", event_value=Decimal("3.0"))
        add_transactions([transaction_1], db_session)

        latest_block_number = get_latest_block_number_from_table(HyperdriveTransaction, db_session)
        assert latest_block_number == 1

        transaction_2 = HyperdriveTransaction(block_number=2, transaction_hash="b", event_value=Decimal("3.2"))
        transaction_3 = HyperdriveTransaction(block_number=3, transaction_hash="c", event_value=Decimal("3.4"))
        add_transactions([transaction_2, transaction_3], db_session)

        latest_block_number = get_latest_block_number_from_table(HyperdriveTransaction, db_session)
        assert latest_block_number == 3

    @pytest.mark.docker
    def test_get_transactions(self, db_session):
        """Testing retrieval of transactions via interface"""
        transaction_1 = HyperdriveTransaction(block_number=0, transaction_hash="a", event_value=Decimal("3.1"))
        transaction_2 = HyperdriveTransaction(block_number=1, transaction_hash="b", event_value=Decimal("3.2"))
        transaction_3 = HyperdriveTransaction(block_number=2, transaction_hash="c", event_value=Decimal("3.3"))
        add_transactions([transaction_1, transaction_2, transaction_3], db_session)

        transactions_df = get_transactions(db_session)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.1, 3.2, 3.3])

    @pytest.mark.docker
    def test_block_query_transactions(self, db_session):
        """Testing querying by block number of transactions via interface"""
        transaction_1 = HyperdriveTransaction(block_number=0, transaction_hash="a", event_value=Decimal("3.1"))
        transaction_2 = HyperdriveTransaction(block_number=1, transaction_hash="b", event_value=Decimal("3.2"))
        transaction_3 = HyperdriveTransaction(block_number=2, transaction_hash="c", event_value=Decimal("3.3"))
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

    @pytest.mark.docker
    def test_get_checkpoints(self, db_session):
        """Testing retrieval of checkpoints via interface"""
        checkpoint_time_1 = 100
        checkpoint_time_2 = 1000
        checkpoint_time_3 = 10000
        checkpoint_1 = CheckpointInfo(checkpoint_time=checkpoint_time_1)
        checkpoint_2 = CheckpointInfo(checkpoint_time=checkpoint_time_2)
        checkpoint_3 = CheckpointInfo(checkpoint_time=checkpoint_time_3)
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
        checkpoint_1 = CheckpointInfo(checkpoint_time=100, vault_share_price=Decimal("3.1"))
        checkpoint_2 = CheckpointInfo(checkpoint_time=1000, vault_share_price=Decimal("3.2"))
        checkpoint_3 = CheckpointInfo(checkpoint_time=10000, vault_share_price=Decimal("3.3"))
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
        checkpoint_1 = CheckpointInfo(checkpoint_time=100, vault_share_price=Decimal("3.1"))
        add_checkpoint_info(checkpoint_1, db_session)
        checkpoint_df_1 = get_checkpoint_info(db_session, coerce_float=False)
        assert len(checkpoint_df_1) == 1
        assert checkpoint_df_1.loc[0, "vault_share_price"] == Decimal("3.1")

        # Nothing should happen if we give the same checkpoint info
        checkpoint_2 = CheckpointInfo(checkpoint_time=100, vault_share_price=Decimal("3.1"))
        add_checkpoint_info(checkpoint_2, db_session)
        checkpoint_df_2 = get_checkpoint_info(db_session, coerce_float=False)
        assert len(checkpoint_df_2) == 1
        assert checkpoint_df_2.loc[0, "vault_share_price"] == Decimal("3.1")

        # Adding a checkpoint info with the same checkpoint time with a different value
        # should throw a value error
        checkpoint_3 = CheckpointInfo(checkpoint_time=100, vault_share_price=Decimal("3.4"))
        with pytest.raises(ValueError):
            add_checkpoint_info(checkpoint_3, db_session)


class TestPoolConfigInterface:
    """Testing postgres interface for poolconfig table"""

    @pytest.mark.docker
    def test_get_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(contract_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)

        pool_config_df_1 = get_pool_config(db_session)
        assert len(pool_config_df_1) == 1
        np.testing.assert_array_equal(pool_config_df_1["initial_vault_share_price"], np.array([3.2]))

        pool_config_2 = PoolConfig(contract_address="1", initial_vault_share_price=Decimal("3.4"))
        add_pool_config(pool_config_2, db_session)

        pool_config_df_2 = get_pool_config(db_session)
        assert len(pool_config_df_2) == 2
        np.testing.assert_array_equal(pool_config_df_2["initial_vault_share_price"], np.array([3.2, 3.4]))

    @pytest.mark.docker
    def test_primary_id_query_pool_config(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config = PoolConfig(contract_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config, db_session)

        pool_config_df_1 = get_pool_config(db_session, contract_address="0")
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initial_vault_share_price"] == 3.2

        pool_config_df_2 = get_pool_config(db_session, contract_address="1")
        assert len(pool_config_df_2) == 0

    @pytest.mark.docker
    def test_pool_config_verify(self, db_session):
        """Testing retrieval of pool config via interface"""
        pool_config_1 = PoolConfig(contract_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_1, db_session)
        pool_config_df_1 = get_pool_config(db_session)
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initial_vault_share_price"] == 3.2

        # Nothing should happen if we give the same pool_config
        pool_config_2 = PoolConfig(contract_address="0", initial_vault_share_price=Decimal("3.2"))
        add_pool_config(pool_config_2, db_session)
        pool_config_df_2 = get_pool_config(db_session)
        assert len(pool_config_df_2) == 1
        assert pool_config_df_2.loc[0, "initial_vault_share_price"] == 3.2

        # If we try to add another pool config with a different value, should throw a ValueError
        pool_config_3 = PoolConfig(contract_address="0", initial_vault_share_price=Decimal("3.4"))
        with pytest.raises(ValueError):
            add_pool_config(pool_config_3, db_session)


class TestPoolInfoInterface:
    """Testing postgres interface for poolinfo table"""

    @pytest.mark.docker
    def test_latest_block_number(self, db_session):
        """Testing latest block number call"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(block_number=1, timestamp=timestamp_1)
        add_pool_infos([pool_info_1], db_session)

        latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
        assert latest_block_number == 1

        timestamp_1 = datetime.fromtimestamp(1628472002)
        pool_info_1 = PoolInfo(block_number=2, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472004)
        pool_info_2 = PoolInfo(block_number=3, timestamp=timestamp_2)
        add_pool_infos([pool_info_1, pool_info_2], db_session)

        latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
        assert latest_block_number == 3

    @pytest.mark.docker
    def test_get_pool_info(self, db_session):
        """Testing retrieval of pool info via interface"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(block_number=0, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(block_number=1, timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(block_number=2, timestamp=timestamp_3)
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
        pool_info_1 = PoolInfo(block_number=0, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(block_number=1, timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(block_number=2, timestamp=timestamp_3)
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


class TestWalletDeltaInterface:
    """Testing postgres interface for walletinfo table"""

    @pytest.mark.docker
    def test_latest_block_number(self, db_session):
        """Testing retrieval of wallet info via interface"""
        wallet_delta_1 = WalletDelta(block_number=1, transaction_hash="a", delta=Decimal("3.0"))
        add_wallet_deltas([wallet_delta_1], db_session)
        latest_block_number = get_latest_block_number_from_table(WalletDelta, db_session)
        assert latest_block_number == 1
        wallet_delta_2 = WalletDelta(block_number=2, transaction_hash="a", delta=Decimal("3.2"))
        wallet_delta_3 = WalletDelta(block_number=3, transaction_hash="a", delta=Decimal("3.4"))
        add_wallet_deltas([wallet_delta_2, wallet_delta_3], db_session)
        latest_block_number = get_latest_block_number_from_table(WalletDelta, db_session)
        assert latest_block_number == 3

    @pytest.mark.docker
    def test_get_wallet_delta(self, db_session):
        """Testing retrievals of walletinfo via interface"""
        wallet_delta_1 = WalletDelta(block_number=0, transaction_hash="a", delta=Decimal("3.1"))
        wallet_delta_2 = WalletDelta(block_number=1, transaction_hash="a", delta=Decimal("3.2"))
        wallet_delta_3 = WalletDelta(block_number=2, transaction_hash="a", delta=Decimal("3.3"))
        add_wallet_deltas([wallet_delta_1, wallet_delta_2, wallet_delta_3], db_session)
        # Since we're testing this in isolation without poolinfo, we can't return timestamp here
        # otherwise no data is returned.
        wallet_delta_df = get_wallet_deltas(db_session, return_timestamp=False)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.1, 3.2, 3.3]))

    @pytest.mark.docker
    def test_block_query_wallet_delta(self, db_session):
        """Testing querying by block number of wallet info via interface"""
        wallet_delta_1 = WalletDelta(block_number=0, transaction_hash="a", delta=Decimal("3.1"))
        wallet_delta_2 = WalletDelta(block_number=1, transaction_hash="a", delta=Decimal("3.2"))
        wallet_delta_3 = WalletDelta(block_number=2, transaction_hash="a", delta=Decimal("3.3"))
        add_wallet_deltas([wallet_delta_1, wallet_delta_2, wallet_delta_3], db_session)
        wallet_delta_df = get_wallet_deltas(db_session, start_block=1, return_timestamp=False)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.2, 3.3]))
        wallet_delta_df = get_wallet_deltas(db_session, start_block=-1, return_timestamp=False)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.3]))
        wallet_delta_df = get_wallet_deltas(db_session, end_block=1, return_timestamp=False)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.1]))
        wallet_delta_df = get_wallet_deltas(db_session, end_block=-1, return_timestamp=False)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.1, 3.2]))
        wallet_delta_df = get_wallet_deltas(db_session, start_block=1, end_block=-1, return_timestamp=False)
        np.testing.assert_array_equal(wallet_delta_df["delta"], np.array([3.2]))

    @pytest.mark.docker
    def test_get_agents(self, db_session):
        """Testing helper function to get current wallet values"""
        wallet_delta_1 = WalletDelta(block_number=0, transaction_hash="a", wallet_address="addr_1")
        wallet_delta_2 = WalletDelta(block_number=1, transaction_hash="b", wallet_address="addr_1")
        wallet_delta_3 = WalletDelta(block_number=2, transaction_hash="c", wallet_address="addr_2")
        add_wallet_deltas([wallet_delta_1, wallet_delta_2, wallet_delta_3], db_session)
        agents = get_all_traders(db_session).to_list()
        assert len(agents) == 2
        assert "addr_1" in agents
        assert "addr_2" in agents


class TestCurrentWalletInterface:
    """Testing postgres interface for CurrentWallet table"""

    @pytest.mark.docker
    def test_latest_block_number(self, db_session):
        """Testing retrieval of wallet info via interface"""
        wallet_info_1 = CurrentWallet(block_number=1, value=Decimal("3.0"))
        add_current_wallet([wallet_info_1], db_session)
        latest_block_number = get_latest_block_number_from_table(CurrentWallet, db_session)
        assert latest_block_number == 1
        wallet_info_2 = CurrentWallet(block_number=2, value=Decimal("3.2"))
        wallet_info_3 = CurrentWallet(block_number=3, value=Decimal("3.4"))
        add_current_wallet([wallet_info_2, wallet_info_3], db_session)
        latest_block_number = get_latest_block_number_from_table(CurrentWallet, db_session)
        assert latest_block_number == 3

    @pytest.mark.docker
    def test_get_current_wallet(self, db_session):
        """Testing retrieval of walletinfo via interface"""
        wallet_info_1 = CurrentWallet(block_number=0, wallet_address="a", value=Decimal("3.1"))
        wallet_info_2 = CurrentWallet(block_number=1, wallet_address="b", value=Decimal("3.2"))
        wallet_info_3 = CurrentWallet(block_number=2, wallet_address="c", value=Decimal("3.3"))
        add_current_wallet([wallet_info_1, wallet_info_2, wallet_info_3], db_session)
        wallet_info_df = get_current_wallet(db_session)
        # Sort by value to make order invariant
        wallet_info_df = wallet_info_df.sort_values(by=["value"])
        np.testing.assert_array_equal(wallet_info_df["value"], np.array([3.1, 3.2, 3.3]))

    @pytest.mark.docker
    def test_block_query_wallet_info(self, db_session):
        """Testing querying by block number of wallet info via interface"""
        wallet_info_1 = CurrentWallet(block_number=0, wallet_address="a", value=Decimal("3.1"))
        wallet_info_2 = CurrentWallet(block_number=1, wallet_address="b", value=Decimal("3.2"))
        wallet_info_3 = CurrentWallet(block_number=2, wallet_address="c", value=Decimal("3.3"))
        add_current_wallet([wallet_info_1, wallet_info_2, wallet_info_3], db_session)
        wallet_info_df = get_current_wallet(db_session, end_block=1)
        np.testing.assert_array_equal(wallet_info_df["value"], np.array([3.1]))
        wallet_info_df = get_current_wallet(db_session, end_block=-1)
        # Sort by value to make order invariant
        wallet_info_df = wallet_info_df.sort_values(by=["value"])
        np.testing.assert_array_equal(wallet_info_df["value"], np.array([3.1, 3.2]))

    @pytest.mark.docker
    def test_current_wallet_info(self, db_session):
        """Testing helper function to get current wallet values"""
        wallet_info_1 = CurrentWallet(
            block_number=0, wallet_address="addr", token_type=BASE_TOKEN_SYMBOL, value=Decimal("3.1")
        )
        wallet_info_2 = CurrentWallet(block_number=1, wallet_address="addr", token_type="LP", value=Decimal("5.1"))
        add_current_wallet([wallet_info_1, wallet_info_2], db_session)
        wallet_info_df = get_current_wallet(db_session).reset_index()
        # Sort by value to make order invariant
        wallet_info_df = wallet_info_df.sort_values(by=["value"])
        np.testing.assert_array_equal(wallet_info_df["token_type"], [BASE_TOKEN_SYMBOL, "LP"])
        np.testing.assert_array_equal(wallet_info_df["value"], [3.1, 5.1])
        # E.g., block 2, wallet base tokens gets updated to 6.1
        wallet_info_3 = CurrentWallet(
            block_number=2, wallet_address="addr", token_type=BASE_TOKEN_SYMBOL, value=Decimal("6.1")
        )
        add_current_wallet([wallet_info_3], db_session)
        wallet_info_df = get_current_wallet(db_session).reset_index()
        # Sort by value to make order invariant
        wallet_info_df = wallet_info_df.sort_values(by=["value"])
        np.testing.assert_array_equal(wallet_info_df["token_type"], ["LP", BASE_TOKEN_SYMBOL])
        np.testing.assert_array_equal(wallet_info_df["value"], [5.1, 6.1])
