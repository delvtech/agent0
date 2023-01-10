import unittest
from elfpy.agent import Agent

from elfpy.markets import Market
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.types import MarketAction, MarketActionType, MarketState, StretchedTime


# FIXME: We should use the LP reserves in spot price and APR calculations.
class TestLP(unittest.TestCase):

    # TODO: This should handle interest accrual.
    def test_lp(self):
        time = 0
        alice = Agent(wallet_address=0, budget=200_000)
        bob = Agent(wallet_address=1, budget=1000_000)

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

        # TODO: We should arguably have much fewer arguments for these functions.
        # Why do we have to pass a full MarketAction structure?
        #
        # Bob buys a large long.
        (market_deltas, wallet_deltas) = market._open_long(
            agent_action=MarketAction(
                action_type=MarketActionType.OPEN_LONG,
                wallet_address=bob.wallet.address,
                trade_amount=min(
                    pricing_model.get_max_long(
                        market_state=market.market_state,
                        fee_percent=market.fee_percent,
                        time_remaining=market.position_duration,
                    ),
                    bob.wallet.base,
                ),
                mint_time=time,
            ),
            time_remaining=market.position_duration,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Time passes
        time = 0.9
        market.tick(0.9)

        # Add liquidity to the market.
        (market_deltas, wallet_deltas) = market._add_liquidity(
            agent_action=MarketAction(
                action_type=MarketActionType.ADD_LIQUIDITY,
                wallet_address=alice.wallet.address,
                trade_amount=alice.wallet.base,
                mint_time=time,
            ),
            time_remaining=position_duration,
        )
        market.market_state.apply_delta(market_deltas)
        alice.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Bob immediately closes the long.
        (mint_time, long_amount) = list(bob.wallet.longs.items())[0]
        (market_deltas, wallet_deltas) = market._close_long(
            agent_action=MarketAction(
                action_type=MarketActionType.CLOSE_LONG,
                wallet_address=bob.wallet.address,
                trade_amount=long_amount,
                mint_time=mint_time,
            ),
            time_remaining=market.position_duration,
        )
        market.market_state.apply_delta(market_deltas)
        bob.update_wallet(wallet_deltas=wallet_deltas, market=market)

        # Alice closes her LP position.
        (market_deltas, wallet_deltas) = market._remove_liquidity(
            agent_action=MarketAction(
                action_type=MarketActionType.REMOVE_LIQUIDITY,
                wallet_address=alice.wallet.address,
                trade_amount=alice.wallet.lp_tokens,
                mint_time=time,
            ),
            time_remaining=position_duration,
        )
        market.market_state.apply_delta(market_deltas)
        alice.update_wallet(wallet_deltas=wallet_deltas, market=market)
