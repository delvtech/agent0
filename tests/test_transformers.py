# %%
"""Utilities to transform from elf-simulations to Ape objects."""
from __future__ import annotations

import logging
import unittest

from pathlib import Path

import ape
from ape.api import ReceiptAPI

import elfpy
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_pricing_model as hyperdrive_pm
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.outputs as output_utils
import elfpy.utils.transformers as trans_utils
from elfpy.agents.agent import Agent
from elfpy.agents.policies import RandomAgent
from elfpy.simulators.config import Config
from elfpy.utils import sim_utils


class TransformerTest(unittest.TestCase):
    """Test class for Transformers."""

    # pylint: disable=too-few-public-methods
    __test__ = False

    def __init__(self):
        config = Config()

        config.title = "transformers demo"
        config.pricing_model_name = "Hyperdrive"  # can be yieldspace or hyperdrive

        config.num_trading_days = 3  # Number of simulated trading days
        config.num_blocks_per_day = 1  # Blocks in a given day (7200 means ~12 sec per block)
        config.num_position_days = 365
        config.curve_fee_multiple = 0.10  # fee multiple applied to the price slippage (1-p) collected on trades
        config.flat_fee_multiple = 0.005  # 5 bps

        config.target_fixed_apr = 0.01  # target fixed APR of the initial market after the LP
        config.target_liquidity = 500_000_000  # target total liquidity of the initial market, before any trades

        config.log_level = logging.ERROR  # Logging level, should be in [DEBUG, INFO, WARNING]
        config.log_filename = "transformers"  # Output filename for logging
        config.freeze()

        # %% setup
        output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)
        simulator = sim_utils.get_simulator(config)
        agent_policy = RandomAgent(rng=simulator.rng)
        agent = Agent(wallet_address=1, policy=agent_policy)
        simulator.add_agents([agent])
        agent_ids = list(simulator.agents)
        trades = simulator.collect_trades(agent_ids)

        # %% fixtures (stuff I use elesewhere)
        self.provider = ape.networks.parse_network_choice("ethereum:local:foundry").push_provider()
        project: ape_utils.HyperdriveProject = ape_utils.HyperdriveProject(path=Path.cwd())
        self.test_account = ape.accounts.test_accounts[0]
        self.test_account.balance += int(1e18)  # give test account 1 Eth
        self.base_instance = self.test_account.deploy(project.get_contract("ERC20Mintable"))
        self.pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        self.hyperdrive_instance = ape_utils.deploy_hyperdrive(
            config, self.base_instance, self.test_account, self.pricing_model, project
        )
        # why is this so awkward? we packed "market" next to the Trade class in a tuple, instead of inside
        _, trade_obj = trades[0]
        self.trade_details = trade_obj.trade
        # mint 50k base
        self.base_instance.mint(self.test_account.address, int(50_000 * 1e18), sender=self.test_account)
        # approve 50k base, using attempt_txn cus this txn has to be signed
        ape_utils.attempt_txn(
            self.test_account, self.base_instance.approve, self.hyperdrive_instance.address, int(50_000 * 1e18)
        )
        super().__init__()


@unittest.skip("not working yet")
def test_trans_lib_abi_call():
    """TRASFORMERS ROLL OUT: TRADE_DETAILS => ABI_CALL (issue #397)."""
    test = TransformerTest()

    # build params kwargs to pass to ape_trade
    params = {
        "trade_type": test.trade_details.action_type.name,
        "hyperdrive_contract": test.hyperdrive_instance,
        "agent": test.test_account,
        "amount": test.trade_details.trade_amount.scaled_value,  # ape works with ints
    }
    if test.trade_details.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
        params["maturity_time"] = int(test.trade_details.mint_time + elfpy.SECONDS_IN_YEAR)
    # execute the trade using key-word arguments
    _, txn_receipt_result = ape_utils.ape_trade(**params)
    assert isinstance(txn_receipt_result, ReceiptAPI), "ape_trade did not return Receipt"
    txn_receipt: ReceiptAPI = txn_receipt_result
    assert txn_receipt.failed is not True, "txn was not successfull"

    # show that we can return whichever part of the "abi call" you want, without executing it!
    manual_contract_txn, manual_args, manual_abi = ape_utils.create_trade(**params)
    trans_lib_contract_txn, trans_lib_args, trans_lib_abi = trans_utils.trade_details_to_abi(
        trade_details=test.trade_details,
        hyperdrive_instance=test.hyperdrive_instance,
        account=test.test_account,
    )

    # check that the two are the same
    assert trans_lib_contract_txn == manual_contract_txn, "contract_txn is different"
    assert trans_lib_args == manual_args, "args are different"
    assert trans_lib_abi == manual_abi, "abi is different"


@unittest.skip("not working yet")
def test_trans_lib_market_state() -> hyperdrive_market.HyperdriveMarketState:
    """TRASFORMERS ROLL OUT: getPoolInfo, getPoolConfig --> MarketState (issue #391)."""
    test = TransformerTest()
    return ape_utils.get_market_state_from_contract(hyperdrive_contract=test.hyperdrive_instance)


@unittest.skip("not working yet")
def test_trans_lib_wallet():
    """TRANSFORMERS ROLL OUT: tx_receipt --> Wallet (issue #392)."""
    test = TransformerTest()
    return ape_utils.get_wallet_from_onchain_trade_info(
        address=test.test_account.address,
        index=1,  # index of the agent in the list of ALL agents, assigned in set_up_agents() to len(sim_agents)
        info=ape_utils.get_on_chain_trade_info(test.hyperdrive_instance),
        hyperdrive_contract=test.hyperdrive_instance,
        base_contract=test.base_instance,
    )


@unittest.skip("not working yet")
def test_trans_lib_elfpy_market():
    """TRANSFORMERS ROLL OUT: getPoolinfo --> market_deltas (issue #395)."""
    test = TransformerTest()
    # TODO: replace with market_deltas instead of elfpy_market
    hyperdrive_config = ape_utils.get_hyperdrive_config(test.hyperdrive_instance)
    latest_block = ape.chain.blocks[-1]
    block_number = latest_block.number
    assert block_number, "block number isn't real"
    start_timestamp = ape.chain.blocks[-1].timestamp
    block_timestamp = latest_block.timestamp
    elfpy_market = ape_utils.create_elfpy_market(
        test.pricing_model, test.hyperdrive_instance, hyperdrive_config, block_number, block_timestamp, start_timestamp
    )
    assert elfpy_market, "we don't have an elfpy market"
