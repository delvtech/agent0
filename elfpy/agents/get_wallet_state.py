"""Gets all the state variables in a wallet."""
from __future__ import annotations

from elfpy.agents import wallet
from elfpy.markets.hyperdrive import hyperdrive_actions, hyperdrive_market
from elfpy.math import FixedPoint


def get_wallet_state(agent_wallet: wallet.Wallet, market: hyperdrive_market.Market) -> dict[str, FixedPoint]:
    r"""The wallet's current state of public variables

    .. todo:: This will go away once we finish refactoring the state
    """
    lp_token_value = FixedPoint(0)
    # proceed further only if the agent has LP tokens and avoid divide by zero
    if agent_wallet.lp_tokens > FixedPoint(0) and market.market_state.lp_total_supply > FixedPoint(0):
        share_of_pool = agent_wallet.lp_tokens / market.market_state.lp_total_supply
        pool_value = (
            market.market_state.bond_reserves * market.spot_price  # in base
            + market.market_state.share_reserves * market.market_state.share_price  # in base
        )
        lp_token_value = pool_value * share_of_pool  # in base
    share_reserves = market.market_state.share_reserves
    # compute long values in units of base
    longs_value = FixedPoint(0)
    longs_value_no_mock = FixedPoint(0)
    for mint_time, long in agent_wallet.longs.items():
        if long.balance > FixedPoint(0) and share_reserves:
            balance = hyperdrive_actions.calc_close_long(
                bond_amount=long.balance,
                market_state=market.market_state,
                position_duration=market.position_duration,
                pricing_model=market.pricing_model,
                block_time=market.block_time.time,
                mint_time=mint_time,
                is_trade=True,
            )[1].balance.amount
        else:
            balance = FixedPoint(0)
        longs_value += balance
        longs_value_no_mock += long.balance * market.spot_price
    # compute short values in units of base
    shorts_value = FixedPoint(0)
    shorts_value_no_mock = FixedPoint(0)
    for mint_time, short in agent_wallet.shorts.items():
        balance = FixedPoint(0)
        if (
            short.balance > FixedPoint(0)
            and share_reserves > FixedPoint(0)
            and market.market_state.bond_reserves - market.market_state.bond_buffer > short.balance
        ):
            balance = hyperdrive_actions.calc_close_short(
                bond_amount=short.balance,
                market_state=market.market_state,
                position_duration=market.position_duration,
                pricing_model=market.pricing_model,
                block_time=market.block_time.time,
                mint_time=mint_time,
                open_share_price=short.open_share_price,
            )[1].balance.amount
        shorts_value += balance
        base_no_mock = short.balance * (FixedPoint("1.0") - market.spot_price)
        shorts_value_no_mock += base_no_mock
    return {
        f"agent_{agent_wallet.address}_base": agent_wallet.balance.amount,
        f"agent_{agent_wallet.address}_lp_tokens": lp_token_value,
        f"agent_{agent_wallet.address}_num_longs": FixedPoint(len(agent_wallet.longs)),
        f"agent_{agent_wallet.address}_num_shorts": FixedPoint(len(agent_wallet.shorts)),
        f"agent_{agent_wallet.address}_total_longs": longs_value,
        f"agent_{agent_wallet.address}_total_shorts": shorts_value,
        f"agent_{agent_wallet.address}_total_longs_no_mock": longs_value_no_mock,
        f"agent_{agent_wallet.address}_total_shorts_no_mock": shorts_value_no_mock,
    }
