import unittest
from elfpy.agent import Agent

from elfpy.markets import Market
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.types import MarketState, StretchedTime


# FIXME: We should use the LP reserves in spot price and APR calculations.
#
# FIXME: This should handle interest accrual.
class TestLP(unittest.TestCase):
    def test_lp_scenario_1(self):
        # Instantiate the pricing model.
        pricing_model = HyperdrivePricingModel()

        # Instantiate the market.
        target_apr = 0.05
        position_duration = StretchedTime(days=182.5, time_stretch=pricing_model.calc_time_stretch(0.05))
        share_reserves = 1_000_000
        bond_reserves = pricing_model.calc_bond_reserves(
            target_apr=target_apr,
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
        charlie.wallet.lp_tokens = (
            market.market_state.share_price * market.market_state.share_reserves + market.market_state.bond_reserves
        )
        bob = Agent(wallet_address=1, budget=1000_000)

        # Bob buys a large long.
        (market_deltas, wallet_deltas) = market.open_long(
            wallet_address=bob.wallet.address,
            trade_amount=bob.get_max_long(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Time passes
        dt = 0.95
        market.tick(dt)
        market.accrue(apr=0.05, delta_time=dt)

        # Bob immediately closes the long.
        (mint_time, long_amount) = list(bob.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market.close_long(
            wallet_address=bob.wallet.address,
            trade_amount=long_amount,
            mint_time=mint_time,
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

        print(f"\n{charlie.wallet=}")
        print(f"{bob.wallet=}")

    def test_lp_scenario_2(self):
        # Instantiate the pricing model.
        pricing_model = HyperdrivePricingModel()

        # Instantiate the market.
        target_apr = 0.05
        position_duration = StretchedTime(days=182.5, time_stretch=pricing_model.calc_time_stretch(0.05))
        share_reserves = 1_000_000
        bond_reserves = pricing_model.calc_bond_reserves(
            target_apr=target_apr,
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
        charlie.wallet.lp_tokens = (
            market.market_state.share_price * market.market_state.share_reserves + market.market_state.bond_reserves
        )
        bob = Agent(wallet_address=1, budget=1000_000)
        alice = Agent(wallet_address=2, budget=200_000)

        # Bob buys a large long.
        (market_deltas, wallet_deltas) = market.open_long(
            wallet_address=bob.wallet.address,
            trade_amount=bob.get_max_long(market=market),
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Time passes
        dt = 0.95
        market.tick(dt)
        market.accrue(apr=0.05, delta_time=dt)

        # Add liquidity to the market.
        (market_deltas, wallet_deltas) = market.add_liquidity(
            wallet_address=alice.wallet.address,
            trade_amount=alice.wallet.base,
        )
        market.market_state.apply_delta(market_deltas)
        alice.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob immediately closes the long.
        (mint_time, long_amount) = list(bob.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market.close_long(
            wallet_address=bob.wallet.address,
            trade_amount=long_amount,
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

        print(f"\n{charlie.wallet=}")
        print(f"{bob.wallet=}")
        print(f"{alice.wallet=}")
