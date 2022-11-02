"""
example logic here:
https://github.com/nadirizr/json-logic-py/blob/master/json_logic/__init__.py
"""


def if_(*args):
    """Implements the 'if' operator with support for multiple elseif-s."""
    for i in range(0, len(args) - 1, 2):
        if args[i]:
            return args[i + 1]
    if len(args) % 2:
        return args[-1]
    else:
        return None


def greater(a, b):
    """Implements the '>' operator"""
    return less(b, a)


def less(a, b):
    """Implements the '<' operator"""
    types = set([type(a), type(b)])
    if float in types or int in types:
        try:
            a, b = float(a), float(b)
        except TypeError:
            return False # NaN
    return a < b


def hard_equals(a, b):
    """Implements the '===' operator."""
    if isinstance(a, b):
        return False
    return a == b


def greater_or_equal(a, b):
    """Implements the '>=' operator."""
    return less_or_equal(b, a)


def less_or_equal(a, b):
    """Implements the '<=' operator."""
    return less(a, b) or hard_equals(a, b)


operations = {
    "if": if_,
    ">": greater,
    "gt": greater,
    "<": less,
    "lt": less,
    "<=": less_or_equal,
    ">=": greater_or_equal,
    "==": hard_equals,
}


def get_variable(arg, market, rng):
    """Parse the market class to get an argument"""
    if "market" in arg:
        attr = arg.split(".")[-1] # get the desired market attribute
        return getattr(market, attr)
    if "rand_variable" in arg:
        arg = parse_distribution(arg["rand_variable"], rng)
    return arg


def parse_conditional(market, conditional, rng):
    """Parse conditional spec"""
    operation = conditional[0]
    arg1 = get_variable(conditional[1], market, rng)
    arg2 = get_variable(conditional[2], market, rng)
    return operations[operation](arg1, arg2)


def parse_distribution(dist_spec, rng):
    """Return a distribution described by the method policy"""
    if dist_spec["distribution"] == "gaussian":
        return rng.gaussian(dist_spec["mean"], dist_spec["std"])
    elif dist_spec["distribution"] == "integers":
        return rng.integers(low=dist_spec["low"], high=dist_spec["high"])
    raise ValueError(f'Only ["gaussian", "integers"] distributions are supported, not {dist_spec["distribution"]}')


def parse_trade(trade_spec, market, rng):
    """Parse the trade specification"""
    if "conditional" in trade_spec:
        action_resolution = parse_conditional(trade_spec["conditional"]["if"], market, rng)
        if action_resolution:
            action = parse_action(trade_spec["conditional"]["then"], rng)
        else:
            action = parse_action(trade_spec["conditional"]["else"], rng)
    else:
        action = parse_action(trade_spec, rng)
    return action


def parse_action(action_spec, rng):
    """Parse the action specification"""
    if action_spec == "none":
        return None
    if action_spec == "buy":
        token_in = "base"
        token_out = "pt"
        amount = parse_trade_amount(action_spec["buy"], rng)
    elif action_spec == "sell":
        token_in = "pt"
        token_out = "base"
        amount = parse_trade_amount(action_spec["sell"], rng)
    else:
        raise ValueError(
            f'parse_json: ERROR: action_spec must be ["buy", "sell", "none"], not {action_spec}')
    return (token_in, token_out, amount)


def parse_trade_amount(amount_spec, rng):
    """Return a trade amount"""
    if "method" in amount_spec:
        amount = parse_distribution(amount_spec["amount"], rng)
    else:
        amount = amount_spec["amount"]
    return amount
