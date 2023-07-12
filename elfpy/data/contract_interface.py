"""Functions and classes for interfacing with smart contracts"""
from __future__ import annotations

import json
import logging
import os
import time

from datetime import datetime
from typing import Any

import requests

from eth_typing import BlockNumber, URI
from eth_utils import address
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract, ContractEvent, ContractFunction
from web3.middleware import geth_poa
from web3.types import (
    ABI,
    ABIFunctionComponents,
    ABIFunctionParams,
    ABIEvent,
    BlockData,
    EventData,
    LogReceipt,
    RPCEndpoint,
    RPCResponse,
    TxReceipt,
)

from elfpy.data.db_schema import PoolConfig, PoolInfo, Transaction, WalletInfo
from elfpy.eth.accounts import AgentAccount
from elfpy.markets.hyperdrive import hyperdrive_assets

RETRY_COUNT = 10
