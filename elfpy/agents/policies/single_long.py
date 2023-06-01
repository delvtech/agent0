"""User strategy that opens a long position and then closes it after a certain amount of time has passed"""
from __future__ import annotations

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.types as types
from elfpy.math import FixedPoint


class SingleLongAgent(elf_agent.Agent):
    """
    simple long
    only has one long open at a time
    """

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Specify action"""
        longs = list(self.wallet.longs.values())
        has_opened_long = len(longs) > 0
        action_list = []
        if has_opened_long:
            mint_time = list(self.wallet.longs)[-1]
            enough_time_has_passed = market.block_time.time - mint_time > FixedPoint("0.01")
            if enough_time_has_passed:
                action_list.append(
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.HyperdriveMarketAction(
                            action_type=hyperdrive_actions.MarketActionType.CLOSE_LONG,
                            trade_amount=longs[-1].balance,
                            wallet=self.wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        else:
            trade_amount = self.get_max_long(market) / FixedPoint("2.0")
            action_list.append(
                types.Trade(
                    market=types.MarketType.HYPERDRIVE,
                    trade=hyperdrive_actions.HyperdriveMarketAction(
                        action_type=hyperdrive_actions.MarketActionType.OPEN_LONG,
                        trade_amount=trade_amount,
                        wallet=self.wallet,
                    ),
                )
            )
        return action_list
