"""User strategy that opens a single short and doesn't close until liquidation"""
import elfpy.types as types
import elfpy.markets.base as base
import elfpy.markets.hyperdrive as hyperdrive
import elfpy.agents.agent as agent

# pylint: disable=duplicate-code


class Policy(agent.Agent):
    """simple short thatonly has one long open at a time"""

    def __init__(self, wallet_address, budget=100):
        """call basic policy init then add custom stuff"""
        self.amount_to_trade = 100
        super().__init__(wallet_address, budget)

    def action(self, markets: "dict[types.MarketType, base.Market]") -> "list[types.Trade]":
        """
        implement user strategy
        short if you can, only once
        """
        action_list = []
        for market_type, market in markets.items():
            if market_type == types.MarketType.HYPERDRIVE:
                shorts = list(self.wallet.shorts.values())
                has_opened_short = bool(any(short.balance > 0 for short in shorts))
                can_open_short = market.get_max_short(self.wallet) >= self.amount_to_trade
                if can_open_short and not has_opened_short:
                    action_list.append(
                        types.Trade(
                            agent=self.wallet.address,
                            market=types.MarketType.HYPERDRIVE,
                            trade=hyperdrive.MarketAction(
                                action_type=hyperdrive.MarketActionType.OPEN_SHORT,
                                trade_amount=self.amount_to_trade,
                                wallet=self.wallet,
                            ),
                        )
                    )
        return action_list
