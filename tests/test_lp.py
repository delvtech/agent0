import unittest
import logging

from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.types import MarketState, StretchedTime
from elfpy.utils import parse_config as config_utils, outputs as output_utils
from elfpy.wallet import Wallet


# FIXME: Todos
#
# 1. Improve the logging.
#    - The market actions should be logged at an info level.
#    - The logging is too verbose. There shouldn't be newlines after every log
#      if possible.
# 2. Add new scenarios that involve shorts.
# 3. Improve agent trade summary.
#    - The weighted average approach doesn't appear to work for positions that
#      are entered into immediately.
#    - It doesn't do a good job of showing progress. Having the starting budget
#      would make it more readable.
#    - There isn't a field for LP.
class TestLP(unittest.TestCase):
    d_time = 0.5

    def test_lp_scenario_1(self):
        print("-----------------------------------------------------------")
        output_utils.setup_logging(log_level=config_utils.text_to_logging_level("info"))
        logging.info("#0 joins pool, #1 max longs, 0.5 time passes, #1 redeems long, #0 leaves pool")

        # instantiate the pricing model.
        pricing_model = HyperdrivePricingModel()

        # instantiate the market.
        apr = 0.05
        position_duration = StretchedTime(days=182.5, time_stretch=pricing_model.calc_time_stretch(0.05))
        share_reserves = 1_000_000
        bond_reserves = pricing_model.calc_bond_reserves(
            target_apr=apr,
            share_reserves=share_reserves,
            init_share_price=1,
            share_price=1,
            time_remaining=position_duration,
        )
        market = Market(
            pricing_model=pricing_model,
            market_state=MarketState(
                share_reserves=share_reserves,
                bond_reserves=bond_reserves,
                lp_reserves=share_reserves + bond_reserves,
            ),
            position_duration=position_duration,
            fee_percent=0.1,
        )

        # instantiate the agents.
        charlie = Agent(wallet_address=0, budget=0)
        # HACK: How can we make Charlie the initial LP?
        charlie.update_wallet(
            wallet_deltas=Wallet(
                address=charlie.wallet.address,
                base=-charlie.wallet.base,
                lp_tokens=market.market_state.lp_reserves,
            ),
            market=market,
        )
        bob = Agent(wallet_address=1, budget=250_000)

        # bob buys a large long.
        (market_deltas, wallet_deltas) = market.open_long(
            wallet_address=bob.wallet.address,
            trade_amount=bob.get_max_long(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # time passes
        market.tick(self.d_time)
        market.accrue(apr=apr, delta_time=self.d_time)

        # bob immediately closes the long.
        (mint_time, long) = list(bob.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market.close_long(
            wallet_address=bob.wallet.address,
            trade_amount=long.balance,
            mint_time=mint_time,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # charlie closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=charlie.wallet.address,
            trade_amount=charlie.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        charlie.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Log the final reports.
        charlie.log_final_report(market)
        bob.log_final_report(market)

    def test_lp_scenario_2(self):
        print("-----------------------------------------------------------")
        output_utils.setup_logging(log_level=config_utils.text_to_logging_level("info"))
        logging.info(
            "#0 joins pool, #1 max longs, 0.5 time passes, #2 joins pool, #1 redeems long, #2 leaves pool, #0 leaves pool"
        )

        # Instantiate the pricing model.
        pricing_model = HyperdrivePricingModel()

        # Instantiate the market.
        apr = 0.05
        position_duration = StretchedTime(days=182.5, time_stretch=pricing_model.calc_time_stretch(0.05))
        share_reserves = 1_000_000
        bond_reserves = pricing_model.calc_bond_reserves(
            target_apr=apr,
            share_reserves=share_reserves,
            init_share_price=1,
            share_price=1,
            time_remaining=position_duration,
        )
        market = Market(
            pricing_model=pricing_model,
            market_state=MarketState(
                share_reserves=share_reserves,
                bond_reserves=bond_reserves,
                lp_reserves=share_reserves + bond_reserves,
            ),
            position_duration=position_duration,
            fee_percent=0.1,
        )

        # Instantiate the agents.
        charlie = Agent(wallet_address=0, budget=0)
        # HACK: How can we make Charlie the initial LP?
        charlie.update_wallet(
            wallet_deltas=Wallet(
                address=charlie.wallet.address,
                base=-charlie.wallet.base,
                lp_tokens=market.market_state.lp_reserves,
            ),
            market=market,
        )
        bob = Agent(wallet_address=1, budget=250_000)
        alice = Agent(wallet_address=2, budget=200_000)

        # Bob buys a large long.
        (market_deltas, wallet_deltas) = market.open_long(
            wallet_address=bob.wallet.address,
            trade_amount=bob.get_max_long(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Time passes
        market.tick(self.d_time)
        market.accrue(apr=apr, delta_time=self.d_time)

        # Add liquidity to the market.
        (market_deltas, wallet_deltas) = market.add_liquidity(
            wallet_address=alice.wallet.address,
            trade_amount=alice.wallet.base,
        )
        market.market_state.apply_delta(market_deltas)
        alice.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob immediately closes the long.
        (mint_time, long) = list(bob.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market.close_long(
            wallet_address=bob.wallet.address,
            trade_amount=long.balance,
            mint_time=mint_time,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Alice closes her LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=alice.wallet.address,
            trade_amount=alice.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        alice.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Charlie closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=charlie.wallet.address,
            trade_amount=charlie.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        charlie.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Log the final reports.
        charlie.log_final_report(market)
        bob.log_final_report(market)
        alice.log_final_report(market)

    # The direct LP exploit scenario.
    def test_lp_scenario_3(self):
        print("-----------------------------------------------------------")
        output_utils.setup_logging(log_level=config_utils.text_to_logging_level("info"))
        logging.info("#0 joins pool, #1 max longs, #1 joins pool, #1 closes long, #1 leaves pool, #0 leaves pool")

        # Instantiate the pricing model.
        pricing_model = HyperdrivePricingModel()

        # Instantiate the market.
        apr = 0.05
        position_duration = StretchedTime(days=182.5, time_stretch=pricing_model.calc_time_stretch(0.05))
        share_reserves = 1_000_000
        bond_reserves = pricing_model.calc_bond_reserves(
            target_apr=apr,
            share_reserves=share_reserves,
            init_share_price=1,
            share_price=1,
            time_remaining=position_duration,
        )
        market = Market(
            pricing_model=pricing_model,
            market_state=MarketState(
                share_reserves=share_reserves,
                bond_reserves=bond_reserves,
                lp_reserves=share_reserves + bond_reserves,
            ),
            position_duration=position_duration,
            fee_percent=0.1,
        )

        # Instantiate the agents.
        charlie = Agent(wallet_address=0, budget=1_000_000)
        # HACK: How can we make Charlie the initial LP?
        charlie.update_wallet(
            wallet_deltas=Wallet(
                address=charlie.wallet.address,
                base=-charlie.wallet.base,
                lp_tokens=market.market_state.lp_reserves,
            ),
            market=market,
        )
        bob = Agent(wallet_address=1, budget=2_000_000)

        # Bob buys a large long.
        (market_deltas, wallet_deltas) = market.open_long(
            wallet_address=bob.wallet.address,
            trade_amount=bob.get_max_long(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob adds liquidity to the market.
        (market_deltas, wallet_deltas) = market.add_liquidity(
            wallet_address=bob.wallet.address,
            trade_amount=bob.wallet.base,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob immediately closes the long.
        (mint_time, long) = list(bob.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market.close_long(
            wallet_address=bob.wallet.address,
            trade_amount=long.balance,
            mint_time=mint_time,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=bob.wallet.address,
            trade_amount=bob.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Charlie closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=charlie.wallet.address,
            trade_amount=charlie.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        charlie.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Log the final reports.
        charlie.log_final_report(market)
        bob.log_final_report(market)

    # Version of the LP exploit scenario where the exploiter is a trader.
    def test_lp_scenario_4(self):
        print("-----------------------------------------------------------")
        output_utils.setup_logging(log_level=config_utils.text_to_logging_level("info"))
        # TODO: The logging should be good enough that this isn't necessary.
        logging.info("#0 joins pool, #2 max longs, #1 joins pool, #2 closes long, #1 leaves pool, #0 leaves pool")

        # Instantiate the pricing model.
        pricing_model = HyperdrivePricingModel()

        # Instantiate the market.
        apr = 0.05
        position_duration = StretchedTime(days=182.5, time_stretch=pricing_model.calc_time_stretch(0.05))
        share_reserves = 1_000_000
        bond_reserves = pricing_model.calc_bond_reserves(
            target_apr=apr,
            share_reserves=share_reserves,
            init_share_price=1,
            share_price=1,
            time_remaining=position_duration,
        )
        market = Market(
            pricing_model=pricing_model,
            market_state=MarketState(
                share_reserves=share_reserves,
                bond_reserves=bond_reserves,
                lp_reserves=share_reserves + bond_reserves,
            ),
            position_duration=position_duration,
            fee_percent=0.1,
        )

        # Instantiate the agents.
        charlie = Agent(wallet_address=0, budget=1_000_000)
        # HACK: How can we make Charlie the initial LP?
        charlie.update_wallet(
            wallet_deltas=Wallet(
                address=charlie.wallet.address,
                base=-charlie.wallet.base,
                lp_tokens=market.market_state.lp_reserves,
            ),
            market=market,
        )
        bob = Agent(wallet_address=1, budget=1_000_000)
        alice = Agent(wallet_address=2, budget=2_000_000)

        # Alice buys a large long.
        (market_deltas, wallet_deltas) = market.open_long(
            wallet_address=bob.wallet.address,
            trade_amount=alice.get_max_long(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        alice.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob adds liquidity to the market.
        (market_deltas, wallet_deltas) = market.add_liquidity(
            wallet_address=bob.wallet.address,
            trade_amount=bob.wallet.base,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Alice immediately closes the long.
        (mint_time, long) = list(alice.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market.close_long(
            wallet_address=alice.wallet.address,
            trade_amount=long.balance,
            mint_time=mint_time,
        )
        market.market_state.apply_delta(market_deltas)
        alice.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=bob.wallet.address,
            trade_amount=bob.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Charlie closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=charlie.wallet.address,
            trade_amount=charlie.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        charlie.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Log the final reports.
        charlie.log_final_report(market)
        bob.log_final_report(market)
        alice.log_final_report(market)

    # The direct LP exploit scenario.
    def test_lp_scenario_5(self):
        print("-----------------------------------------------------------")
        output_utils.setup_logging(log_level=config_utils.text_to_logging_level("info"))
        logging.info(
            "#0 joins pool, #1 max longs, #1 max shorts, #1 joins pool, #1 closes long, #1 closes short, #1 leaves pool, #0 leaves pool"
        )

        # Instantiate the pricing model.
        pricing_model = HyperdrivePricingModel()

        # Instantiate the market.
        apr = 0.05
        position_duration = StretchedTime(days=182.5, time_stretch=pricing_model.calc_time_stretch(0.05))
        share_reserves = 1_000_000
        bond_reserves = pricing_model.calc_bond_reserves(
            target_apr=apr,
            share_reserves=share_reserves,
            init_share_price=1,
            share_price=1,
            time_remaining=position_duration,
        )
        market = Market(
            pricing_model=pricing_model,
            market_state=MarketState(
                share_reserves=share_reserves,
                bond_reserves=bond_reserves,
                lp_reserves=share_reserves + bond_reserves,
            ),
            position_duration=position_duration,
            fee_percent=0.1,
        )

        # Instantiate the agents.
        charlie = Agent(wallet_address=0, budget=1_000_000)
        # HACK: How can we make Charlie the initial LP?
        charlie.update_wallet(
            wallet_deltas=Wallet(
                address=charlie.wallet.address,
                base=-charlie.wallet.base,
                lp_tokens=market.market_state.lp_reserves,
            ),
            market=market,
        )
        bob = Agent(wallet_address=1, budget=10_000_000)

        # Bob goes maximally long.
        (market_deltas, wallet_deltas) = market.open_long(
            wallet_address=bob.wallet.address,
            trade_amount=bob.get_max_long(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob goes maximally short.
        (market_deltas, wallet_deltas) = market.open_short(
            wallet_address=bob.wallet.address,
            trade_amount=bob.get_max_short(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob adds liquidity to the market.
        (market_deltas, wallet_deltas) = market.add_liquidity(
            wallet_address=bob.wallet.address,
            trade_amount=bob.wallet.base,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob closes his long.
        (mint_time, long) = list(bob.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market.close_long(
            wallet_address=bob.wallet.address,
            trade_amount=long.balance,
            mint_time=mint_time,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob closes his short.
        (mint_time, short) = list(bob.wallet.shorts.items())[0]
        (market_deltas, wallet_deltas) = market.close_short(
            wallet_address=bob.wallet.address,
            trade_amount=short.balance,
            mint_time=mint_time,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=bob.wallet.address,
            trade_amount=bob.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Charlie closes his LP position.
        (market_deltas, wallet_deltas) = market.remove_liquidity(
            wallet_address=charlie.wallet.address,
            trade_amount=charlie.wallet.lp_tokens,
        )
        market.market_state.apply_delta(market_deltas)
        charlie.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Log the final reports.
        charlie.log_final_report(market)
        bob.log_final_report(market)
