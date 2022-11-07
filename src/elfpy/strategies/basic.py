class BasicPolicy:
    """
    most basic policy setup
    """
    def __init__(self, user, policy=[], budget=100):
        """comment"""
        self.user = user
        self.policy = policy
        user.budget = budget

    def get_trade(market):
        """specify action"""
        action_list = []
        # implement trade here
        return action_list