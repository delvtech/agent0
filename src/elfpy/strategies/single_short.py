"""
User strategy that opens a single short and doesn't close until liquidation
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """single short: only has one long open at a time"""

    pt_to_short = 100

    def action(self):
        block_position_list = list(self.wallet.token_in_protocol.values())
        has_opened_short = bool(any((x < -1 for x in block_position_list)))
        max_pt_short = self.get_max_pt_short()
        if not has_opened_short and max_pt_short > 0:
            self.action_list.append(
                self.create_agent_action(
                    action_type="open_short", trade_amount=min(max_pt_short, self.pt_to_short)
                )
            )
        return self.action_list
