"""User strategy that opens a long position and then closes it after a certain amount of time has passed"""

from elfpy.agents.agent import Agent
import elfpy.types as types
import elfpy.markets.hyperdrive as hyperdrive
import elfpy.markets.base as base

# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


class Policy(Agent):
    """
    simple long
    only has one long open at a time
    """

    def action(self, markets: "dict[types.MarketType, base.Market]") -> "list[types.Trade]":
        """Specify action"""
        action_list = []
        for market_type, market in markets:
            if market_type == types.MarketType.HYPERDRIVE:
                longs = list(self.wallet.longs.values())
                has_opened_long = any((long.balance > 0 for long in longs))
                if has_opened_long:
                    mint_time = list(self.wallet.longs)[-1]
                    enough_time_has_passed = market.time - mint_time > 0.01
                    if enough_time_has_passed:
                        action_list.append(
                            types.Trade(
                                agent=self.wallet.address,
                                market=types.MarketType.HYPERDRIVE,
                                trade=hyperdrive.MarketAction(
                                    action_type=hyperdrive.MarketActionType.CLOSE_LONG,
                                    trade_amount=longs[-1].balance,
                                    wallet=self.wallet,
                                    mint_time=mint_time,
                                ),
                            )
                        )
                else:
                    trade_amount = self.get_max_long(market) / 2
                    action_list.append(
                        types.Trade(
                            agent=self,
                            market=types.MarketType.HYPERDRIVE,
                            trade=hyperdrive.MarketAction(
                                action_type=hyperdrive.MarketActionType.OPEN_LONG,
                                trade_amount=trade_amount,
                                wallet=self.wallet,
                            ),
                        )
                    )
        return action_list
