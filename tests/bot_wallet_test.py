"""System test for checking calculated wallets versus wallets on chain"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import cast

from eth_typing import URI
from ethpy import EthConfig
from ethpy.base import smart_contract_read
from ethpy.hyperdrive import AssetIdPrefix, encode_asset_id
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.hyperdrive.api import HyperdriveInterface
from ethpy.test_fixtures.local_chain import DeployedHyperdrivePool
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator as NumpyGenerator
from web3 import HTTPProvider

from agent0 import build_account_key_config_from_agent_config
from agent0.base import MarketType, Trade
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet


def ensure_agent_wallet_is_correct(wallet: HyperdriveWallet, hyperdrive: HyperdriveInterface) -> None:
    """Function to check that the agent's wallet matches what's reported from the chain.
    Will assert that balances match

    Arguments
    ---------
    wallet: HyperdriveWallet
        The HyperdriveWallet object to check against the chain
    hyperdrive: HyperdriveInterface
        The Hyperdrive API interface object
    """
    # Check base
    base_from_chain = smart_contract_read(hyperdrive.base_token_contract, "balanceOf", wallet.address)["value"]
    assert wallet.balance.amount == FixedPoint(scaled_value=base_from_chain)

    # Check lp positions
    asset_id = encode_asset_id(AssetIdPrefix.LP, 0)
    lp_from_chain = smart_contract_read(
        hyperdrive.hyperdrive_contract,
        "balanceOf",
        asset_id,
        wallet.address,
    )["value"]
    assert wallet.lp_tokens == FixedPoint(scaled_value=lp_from_chain)

    # Check withdrawal positions
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    withdrawal_from_chain = smart_contract_read(
        hyperdrive.hyperdrive_contract,
        "balanceOf",
        asset_id,
        wallet.address,
    )["value"]
    assert wallet.withdraw_shares == FixedPoint(scaled_value=withdrawal_from_chain)

    # Check long positions
    for long_time, long_amount in wallet.longs.items():
        asset_id = encode_asset_id(AssetIdPrefix.LONG, long_time)
        long_from_chain = smart_contract_read(
            hyperdrive.hyperdrive_contract,
            "balanceOf",
            asset_id,
            wallet.address,
        )["value"]
        assert long_amount.balance == FixedPoint(scaled_value=long_from_chain)

    # Check short positions
    for short_time, short_amount in wallet.shorts.items():
        asset_id = encode_asset_id(AssetIdPrefix.SHORT, short_time)
        short_from_chain = smart_contract_read(
            hyperdrive.hyperdrive_contract,
            "balanceOf",
            asset_id,
            wallet.address,
        )["value"]
        assert short_amount.balance == FixedPoint(scaled_value=short_from_chain)


class WalletTestAgainstChainPolicy(HyperdrivePolicy):
    """A agent that simply cycles through all trades"""

    @dataclass
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy
        This policy doesn't have any config
        """

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        policy_config: Config | None = None,
    ):
        if policy_config is None:
            policy_config = self.Config()

        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    # We want to rename the argument from "interface" in the base class to "hyperdrive" to be more explicit
    # pylint: disable=arguments-renamed
    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """This agent simply opens all trades for a fixed amount and closes them after, one at a time
        After each trade, the agent will ensure the wallet passed in matches what's on the chain.

        Arguments
        ---------
        hyperdrive : HyperdriveInterface
            The trading market.
        wallet : HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False

        if self.counter == 0:
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=FixedPoint(11111),
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 1:
            # Open Long
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=FixedPoint(22222),
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 2:
            # Open Short
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_SHORT,
                        trade_amount=FixedPoint(33333),
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 3:
            # Remove All Liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                        trade_amount=wallet.lp_tokens,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 4:
            # Close All Longs
            assert len(wallet.longs) == 1
            for long_time, long in wallet.longs.items():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            maturity_time=long_time,
                        ),
                    )
                )
        elif self.counter == 5:
            # Close All Shorts
            assert len(wallet.shorts) == 1
            for short_time, short in wallet.shorts.items():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            # TODO is this actually maturity time? Not mint time?
                            maturity_time=short_time,
                        ),
                    )
                )
        elif self.counter == 6:
            # Redeem all withdrawal shares
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                        trade_amount=wallet.withdraw_shares,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 7:
            # One final check after the previous trade
            pass
        else:
            done_trading = True

        # After each trade, check the wallet for correctness against the chain
        ensure_agent_wallet_is_correct(wallet, hyperdrive)
        self.counter += 1
        return action_list, done_trading


class TestWalletAgainstChain:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    def test_wallet_against_chain(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Runs the entire pipeline and checks the database at the end.
        All arguments are fixtures.
        """
        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"

        # Get hyperdrive chain info
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            random_seed=1234,
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=WalletTestAgainstChainPolicy,
                number_of_agents=1,
                slippage_tolerance=FixedPoint("0.0001"),
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=WalletTestAgainstChainPolicy.Config(),
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            rpc_uri=rpc_uri,
            database_api_uri="not_used",
            # Using default abi dir
        )

        run_agents(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            contract_addresses=hyperdrive_contract_addresses,
            load_wallet_state=False,
        )
