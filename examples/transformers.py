# %%
"""Utilities to transform from elf-simulations to Ape objects."""
from __future__ import annotations
from pathlib import Path
from ape.api import ReceiptAPI
from ape.contracts.base import ContractTransaction
from ethpm_types.abi import MethodABI
from numpy.random._generator import Generator as NumpyGenerator

import ape
import elfpy
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.utils.outputs as output_utils
import elfpy.agents.policies.random_agent as random_agent
import elfpy.markets.hyperdrive.hyperdrive_pricing_model as hyperdrive_pm
from elfpy.simulators.config import Config
from elfpy.utils import sim_utils
from elfpy.math import FixedPoint
import elfpy.utils.apeworx_integrations as ape_utils

# %% setup
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

config.log_level = output_utils.text_to_log_level("WARNING")  # Logging level, should be in ["DEBUG", "INFO", "WARNING"]
config.log_filename = "transformers"  # Output filename for logging
config.freeze()

# %%
class RandomAgent(random_agent.RandomAgent):
    """Agent that randomly opens or closes longs or shorts

    Customized from the policy in that one can force the agent to only open longs or shorts
    """

    def __init__(self, rng: NumpyGenerator, trade_chance_pct: float, wallet_address: int, budget: int = 10_000) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_long = True  # default to allow easy overriding
        self.trade_short = True  # default to allow easy overriding
        super().__init__(rng, trade_chance_pct, wallet_address, FixedPoint(budget * 10 * 18))

    def get_available_actions(
        self,
        disallowed_actions: list[hyperdrive_actions.MarketActionType] | None = None,
    ) -> list[hyperdrive_actions.MarketActionType]:
        """Get all available actions, excluding those listed in disallowed_actions"""
        # override disallowed_actions
        disallowed_actions = []
        if not self.trade_long:  # disallow longs
            disallowed_actions += [
                hyperdrive_actions.MarketActionType.OPEN_LONG,
                hyperdrive_actions.MarketActionType.CLOSE_LONG,
            ]
        if not self.trade_short:  # disallow shorts
            disallowed_actions += [
                hyperdrive_actions.MarketActionType.OPEN_SHORT,
                hyperdrive_actions.MarketActionType.CLOSE_SHORT,
            ]
        # compile a list of all actions
        all_available_actions = [
            hyperdrive_actions.MarketActionType.OPEN_LONG,
            hyperdrive_actions.MarketActionType.OPEN_SHORT,
        ]
        if self.wallet.longs:  # if the agent has open longs
            all_available_actions.append(hyperdrive_actions.MarketActionType.CLOSE_LONG)
        if self.wallet.shorts:  # if the agent has open shorts
            all_available_actions.append(hyperdrive_actions.MarketActionType.CLOSE_SHORT)
        # downselect from all actions to only include allowed actions
        return [action for action in all_available_actions if action not in disallowed_actions]

# %% setup
output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)
simulator = sim_utils.get_simulator(config)
simulator.add_agents([RandomAgent(rng=simulator.rng, trade_chance_pct=1, wallet_address=1, budget=1_000_000)])
agent_ids = list(simulator.agents)
trades = simulator.collect_trades(agent_ids)

# %% why is this so awkward? we packed "market" next to the Trade class in a tuple, instead of inside
market, trade_obj = trades[0]
trade_details = trade_obj.trade

# %% fixtures (stuff I use elesewhere)
provider = ape.networks.parse_network_choice("ethereum:local:foundry").push_provider()
project: ape_utils.HyperdriveProject = ape_utils.HyperdriveProject(path=Path.cwd())
test_account = ape.accounts.test_accounts[0]
test_account.balance += int(1e18)  # give test account 1 Eth
base_instance = test_account.deploy(project.get_contract("ERC20Mintable"))
pricing_model = hyperdrive_pm.HyperdrivePricingModel()
hyperdrive_instance = ape_utils.deploy_hyperdrive(config, base_instance, test_account, pricing_model, project)

# %% TRASFORMERS ROLL OUT: TRADE_DETAILS => ABI_CALL (issue #397)
print(''.join(["="]*8 + [" TRANSFORMERS THE FIRST: TRADE_DETAILS => ABI_CALL"] + ["="]*8))
print(f"{trade_details=}")

amount = trade_details.trade_amount.scaled_value  # ape works with ints
params = {
    "trade_type": trade_details.action_type.name,
    "hyperdrive_contract": hyperdrive_instance,
    "agent": test_account,
    "amount": amount,
}
if trade_details.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
    params["maturity_time"] = int(trade_details.mint_time + elfpy.SECONDS_IN_YEAR)

# mint 50k base
base_instance.mint(test_account.address, int(50_000 * 1e18), sender=test_account)

# approve 50k base, using attempt_txn cus this txn has to be signed
ape_utils.attempt_txn(test_account, base_instance.approve, hyperdrive_instance.address, int(50_000 * 1e18))

# execute the trade using key-word arguments
pool_state, txn_receipt_result = ape_utils.ape_trade(**params)
assert isinstance(txn_receipt_result,ReceiptAPI), "ape_trade did not return Receipt"
txn_receipt: ReceiptAPI = txn_receipt_result
assert txn_receipt.failed is not True, "txn was not successfull"

# show that we can return whichever part of the "abi call" you want, without executing it!
contract_txn: ContractTransaction
args: tuple
abi: MethodABI
contract_txn, args, abi = ape_utils.create_trade(**params)
print(f"{contract_txn=}")
print(f"{args=}")
print(f"{abi=}")

# %% TRASFORMERS ROLL OUT: getPoolInfo, getPoolConfig --> MarketState (issue #391)
market_state=ape_utils.get_market_state_from_contract(hyperdrive_contract=hyperdrive_instance)
print(f"{market_state=}")

# %% TRANSFORMERS ROLL OUT: tx_receipt --> Wallet (issue #392)
# get FOR EVERY tx_receipt that has EVER HAPPENED wow! efficient!
on_chain_trade_info: ape_utils.OnChainTradeInfo = ape_utils.get_on_chain_trade_info(hyperdrive_instance)
agent_wallet = ape_utils.get_wallet_from_onchain_trade_info(
    address_=test_account.address,
    index=1,  # this is the index of the agent in the list of ALL agents, assigned in set_up_agents() to len(sim_agents)
    info=on_chain_trade_info,
    hyperdrive_contract=hyperdrive_instance,
    base_contract=base_instance,
)
print(f"{agent_wallet=}")

# %% TRANSFORMERS ROLL OUT: calculateSpotPrice --> market.SpotPrice (issue #393)
# not sure if i've used this before... I must have... just not recently

# %% TRANSFORMERS ROLL OUT:L calculateAPRFromReserves--> market.fixed_apr (issue #394)
# ditto

# %% TRANSFORMERS ROLL OUT: getPoolinfo --> market_deltas (issue #395)
# I've never done this, because I just create a new market from scratch after every trade
hyperdrive_config = ape_utils.get_hyperdrive_config(hyperdrive_instance)
latest_block = ape.chain.blocks[-1]
block_number = latest_block.number
assert block_number, "block number isn't real"
start_timestamp = ape.chain.blocks[-1].timestamp
block_timestamp = latest_block.timestamp
elfpy_market = ape_utils.create_elfpy_market(
    pricing_model, hyperdrive_instance, hyperdrive_config, block_number, block_timestamp, start_timestamp
)

# %% TRASFORMERS ROLL OUT: TRADE_DETAILS => AGENT_DELTAS (use #396)
print(''.join(["="]*8 + [" TRANSFORMERS THE SECOND: TX_RECEIPT => WALLET"] + ["="]*8))

# use txn_receipt from above
agent_deltas = ape_utils.get_agent_deltas(
    tx_receipt=txn_receipt,  # should pick one of these two names, i like "txn" more than "tx", it's beefier
    trade=???,  # I got this from Jacob
    addresses=agent_ids,
    trade_type=params["trade_type"],
    pool_info=ape_utils.PoolInfo(
        start_time=???,
        block_time=???,
        term_length=???,
        market_state=???,
    )
)
