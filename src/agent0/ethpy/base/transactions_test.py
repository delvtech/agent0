"""Test transaction behavior."""

import logging

import pytest
from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.core.hyperdrive.interactive import ILocalChain, ILocalHyperdrive
from agent0.ethpy.base.transactions import build_transaction


@pytest.mark.anvil
def test_gas_price_base_multiple_explicit(chain: ILocalChain):
    """Set the gas price base multiple explicitly."""
    # set up config, hyperdrive, interface, web3, and agent
    base_fee_multiple = 100
    regular_config = ILocalHyperdrive.Config()
    regular_hyperdrive = ILocalHyperdrive(chain, regular_config)
    regular_interface = regular_hyperdrive.interface
    regular_web3 = regular_interface.web3
    regular_agent = regular_hyperdrive.init_agent(eth=FixedPoint(1))

    fn_args_mint = (
        regular_agent.checksum_address,  # destination
        FixedPoint(11111).scaled_value,  # amount
    )
    regular_built_transaction = build_transaction(
        func_handle=regular_interface.base_token_contract.functions.mint(*fn_args_mint),
        signer=regular_agent.agent,
        web3=regular_web3,
    )
    assert "maxPriorityFeePerGas" in regular_built_transaction
    assert isinstance(regular_built_transaction["maxPriorityFeePerGas"], int)
    regular_priority_fee_per_gas = regular_built_transaction["maxPriorityFeePerGas"]
    assert "maxFeePerGas" in regular_built_transaction
    assert isinstance(regular_built_transaction["maxFeePerGas"], int)
    regular_base_fee_per_gas = regular_built_transaction["maxFeePerGas"] - regular_priority_fee_per_gas

    multiplied_built_transaction = build_transaction(
        func_handle=regular_interface.base_token_contract.functions.mint(*fn_args_mint),
        signer=regular_agent.agent,
        web3=regular_web3,
        txn_options_base_fee_multiple=base_fee_multiple,
    )
    assert "maxPriorityFeePerGas" in multiplied_built_transaction
    assert isinstance(multiplied_built_transaction["maxPriorityFeePerGas"], int)
    multiplied_priority_fee_per_gas = multiplied_built_transaction["maxPriorityFeePerGas"]
    assert "maxFeePerGas" in multiplied_built_transaction
    assert isinstance(multiplied_built_transaction["maxFeePerGas"], int)
    multiplied_base_fee_per_gas = multiplied_built_transaction["maxFeePerGas"] - multiplied_priority_fee_per_gas

    assert multiplied_base_fee_per_gas / regular_base_fee_per_gas == base_fee_multiple


@pytest.mark.anvil
def test_gas_price_priority_multiple_explicit(chain: ILocalChain):
    """Set the gas price priority multiple explicitly."""
    # set up config, hyperdrive, interface, web3, and agent
    priority_fee_multiple = 100
    regular_config = ILocalHyperdrive.Config()
    regular_hyperdrive = ILocalHyperdrive(chain, regular_config)
    regular_interface = regular_hyperdrive.interface
    regular_web3 = regular_interface.web3
    regular_agent = regular_hyperdrive.init_agent(eth=FixedPoint(1))

    fn_args_mint = (
        regular_agent.checksum_address,  # destination
        FixedPoint(11111).scaled_value,  # amount
    )
    regular_built_transaction = build_transaction(
        func_handle=regular_interface.base_token_contract.functions.mint(*fn_args_mint),
        signer=regular_agent.agent,
        web3=regular_web3,
    )
    assert "maxPriorityFeePerGas" in regular_built_transaction
    assert isinstance(regular_built_transaction["maxPriorityFeePerGas"], int)
    regular_priority_fee_per_gas = regular_built_transaction["maxPriorityFeePerGas"]

    multiplied_built_transaction = build_transaction(
        func_handle=regular_interface.base_token_contract.functions.mint(*fn_args_mint),
        signer=regular_agent.agent,
        web3=regular_web3,
        txn_options_priority_fee_multiple=priority_fee_multiple,
    )
    assert "maxPriorityFeePerGas" in multiplied_built_transaction
    assert isinstance(multiplied_built_transaction["maxPriorityFeePerGas"], int)
    multiplied_priority_fee_per_gas = multiplied_built_transaction["maxPriorityFeePerGas"]

    assert multiplied_priority_fee_per_gas / regular_priority_fee_per_gas == priority_fee_multiple


@pytest.mark.anvil
def test_gas_price_priority_multiple_default(chain: ILocalChain):
    """Set the gas price priority multiple as the default."""
    # set up regular and multiplied copies of config, hyperdrive, interface, web3, and agent
    priority_fee_multiple = 100
    regular_config = ILocalHyperdrive.Config()
    multiplied_config = ILocalHyperdrive.Config(txn_options_priority_fee_multiple=priority_fee_multiple)
    regular_hyperdrive = ILocalHyperdrive(chain, regular_config)
    multiplied_hyperdrive = ILocalHyperdrive(chain, multiplied_config)
    regular_interface = regular_hyperdrive.interface
    multiplied_interface = multiplied_hyperdrive.interface
    regular_web3 = regular_interface.web3
    multiplied_web3 = multiplied_interface.web3
    regular_agent = regular_hyperdrive.init_agent(base=FixedPoint(11111), eth=FixedPoint(1))
    multiplied_agent = multiplied_hyperdrive.init_agent(base=FixedPoint(11111), eth=FixedPoint(1))

    regular_agent.add_liquidity(base=FixedPoint(11111))
    latest_block = regular_web3.eth.get_block("latest")
    assert "transactions" in latest_block
    regular_event = latest_block["transactions"][0]
    assert isinstance(regular_event, HexBytes)
    regular_txn_receipt = regular_web3.eth.get_transaction_receipt(regular_event)
    regular_effective_gas_price = regular_txn_receipt["effectiveGasPrice"] / 1e9

    multiplied_agent.add_liquidity(base=FixedPoint(11111))
    latest_block = multiplied_web3.eth.get_block("latest")
    assert "transactions" in latest_block
    multiplied_event = latest_block["transactions"][0]
    assert isinstance(multiplied_event, HexBytes)
    multiplied_txn_receipt = multiplied_web3.eth.get_transaction_receipt(multiplied_event)
    multiplied_effective_gas_price = multiplied_txn_receipt["effectiveGasPrice"] / 1e9

    multiplied_effective_gas_price_floored = int(multiplied_effective_gas_price // 1)
    logging.info(multiplied_effective_gas_price_floored)
    regular_effective_gas_price_floored = int(regular_effective_gas_price // 1)
    logging.info(regular_effective_gas_price_floored)
    assert multiplied_effective_gas_price_floored / regular_effective_gas_price_floored == priority_fee_multiple
