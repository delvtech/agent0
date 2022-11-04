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
    if isinstance(market, dict):
        if "market" in arg:
            attr = arg.split(".")[-1] # get the desired market attribute
            return getattr(market, attr)
        if "rand_variable" in arg:
            arg = parse_distribution(arg["rand_variable"], rng)
    return arg


def parse_conditional(conditional, market, rng):
    """Parse conditional spec"""
    print(f"conditional: {conditional} market: {market} rng: {rng}")
    print(f"comparator {conditional['comparator']}")
    operation = conditional["operator"]
    arg1 = get_variable(conditional["comparator"], market, rng)
    arg2 = get_variable(conditional["value"], market, rng)
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
        print(f"conditional: {trade_spec['conditional']}")
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
    print(f"action_spec: {action_spec}")
    action = list(action_spec)[0]
    spec = action_spec[action]
    if action == "none":
        return None
    if action == "buy":
        token_in = "base"
        token_out = "pt"
    elif action == "sell":
        token_in = "pt"
        token_out = "base"
    else:
        raise ValueError(
            f'parse_json: ERROR: action_spec must be ["buy", "sell", "none"], not {action}')
    input_amount_in_usd = parse_trade_amount(spec, rng)
    return (token_in, token_out, input_amount_in_usd)


def parse_trade_amount(amount_spec, rng):
    """Return a trade amount"""
    if "method" in amount_spec:
        amount = parse_distribution(amount_spec["amount"], rng)
    else:
        amount = amount_spec["amount"]
    if amount <= 0:
        raise ValueError(
            f'parse_trade_amount: ERROR: amount must be >0')
    return amount

def parse(tests, market, rng):
    """
    recursive looping across all items
    not currently used
    adapted from github link at top of this file
    """
    # You've recursed to a primitive, stop!
    if tests is None or not isinstance(tests, dict):
        return tests

    operator = list(tests.keys())[0]
    values = tests[operator]

    # Easy syntax for unary operators, like {"var": "x"} instead of strict {"var": ["x"]}
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]

    # Recursion!
    values = [parse(val, market, rng) for val in values]

    if operator == 'var':
        return get_variable(values, market, rng)
    elif operator == 'amount':
        return values

    if operator not in operations:
        raise ValueError(f"Unrecognized operation {operator}")

    return operations[operator](*values)