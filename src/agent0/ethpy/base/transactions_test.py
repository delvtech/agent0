import logging

from fixedpointmath.fixed_point_integer_math import sign
import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import IHyperdrive, ILocalChain, ILocalHyperdrive
from agent0.ethpy.base.transactions import smart_contract_transact, build_transaction


@pytest.mark.anvil
def test_gas_price_base_multiple_default(chain: ILocalChain):
    """Set the gas price base multiple."""
    # set up regular and multiplied copies of config, hyperdrive, interface, web3, and agent
    regular_config = ILocalHyperdrive.Config()
    multiplied_config = ILocalHyperdrive.Config(txn_options_base_fee_multiple=100)
    regular_hyperdrive = ILocalHyperdrive(chain, regular_config)
    multiplied_hyperdrive = ILocalHyperdrive(chain, multiplied_config)
    regular_interface = regular_hyperdrive.interface
    multiplied_interface = multiplied_hyperdrive.interface
    regular_web3 = regular_interface.web3
    multiplied_web3 = multiplied_interface.web3
    regular_agent = regular_hyperdrive.init_agent(base=FixedPoint(11111))
    multiplied_agent = multiplied_hyperdrive.init_agent(base=FixedPoint(11111))

    # regular_txn_receipt = smart_contract_transact(
    #     regular_web3,
    #     regular_interface.base_token_contract,
    #     regular_agent.agent,
    #     "mint(uint256)",
    #     FixedPoint(11111).scaled_value,
    # )

    regular_fn_args = (
        FixedPoint(11111).scaled_value,
        FixedPoint(0).scaled_value,
        FixedPoint(0).scaled_value,
        (  # IHyperdrive.Options
            regular_agent.checksum_address,  # destination
            False,  # asBase
            bytes(0),  # extraData
        ),
    )
    regular_transaction = build_transaction(
        func_handle=regular_interface.hyperdrive_contract.get_function_by_name("openLong")(*regular_fn_args),
        signer=regular_agent.agent,
        web3=regular_web3,
    )
    logging.info("regualr transaction is %s", regular_transaction)

    # multiplied_txn_receipt = smart_contract_transact(
    #     multiplied_web3,
    #     multiplied_interface.base_token_contract,
    #     multiplied_agent.agent,
    #     "mint(uint256)",
    #     FixedPoint(11111).scaled_value,
    #     txn_options_base_fee_multiple=100,
    # )

    # check gas price
    # logging.info("regular effectiveGasPrice is %s", regular_txn_receipt['effectiveGasPrice'])
    # logging.info("multiplied effectiveGasPrice is %s", multiplied_txn_receipt['effectiveGasPrice'])
    # assert regular_txn_receipt['effectiveGasPrice'] < multiplied_txn_receipt['effectiveGasPrice']


@pytest.mark.anvil
def test_gas_price_priority_multiple(chain: ILocalChain):
    initial_pool_config = ILocalHyperdrive.Config()
    interactive_local_hyperdrive = ILocalHyperdrive(chain, initial_pool_config)
    hyperdrive_config = IHyperdrive.Config(txn_options_priority_fee_multiple=2)