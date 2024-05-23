"""Tests for export data"""

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from .import_export_data import export_db_to_file, import_to_pandas
from .interface import add_pool_config, get_pool_config
from .schema import PoolConfig


# These tests are using fixtures defined in conftest.py
class TestExportImportData:
    """Testing export and import data for precision"""

    @pytest.mark.docker
    def test_export_import(self, db_session):
        """Testing retrieval of transaction via interface"""
        # Write data to database
        # Ensuring decimal format gets preserved
        pool_config = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.22222222222222"))
        add_pool_config(pool_config, db_session)
        # We need pool config as a dataframe, so we read it from the db here
        pool_config_in = get_pool_config(db_session, coerce_float=False)

        # Create a temporary directory
        with TemporaryDirectory() as temp_data_dir:
            temp_data_dir = Path(temp_data_dir)
            export_db_to_file(temp_data_dir, db_session)
            read_pool_config = import_to_pandas(temp_data_dir)["pool_config"]
            assert read_pool_config.equals(pool_config_in)
