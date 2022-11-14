"""
example logic here:
https://github.com/nadirizr/json-logic-py/blob/master/json_logic/__init__.py
"""


def if_(*args):
    """
    Implements the 'if' operator with support for multiple elseif-s
    The first truth in the series is returned

    Arguments
    ---------
    args: any number of comma seperated arguments
        the args are assumed to be a sequence of (bool, val) pairs

    Returns
    -------
    resolution: any
        the resoultion of the first if statement
    """
    for i in range(0, len(args) - 1, 2):  # every other arg is a bool
        if args[i]:  # the even args are conditionals (booleans)
            return args[i + 1]  # the odd args are resolved values
    if len(args) % 2:  # else was included
        return args[-1]  # last statement
    else:  # no else included
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
            return False  # NaN
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


def and_(*args):
    """Implements the 'and' operator."""
    if all(args):
        return True
    else:
        return False


def or_(*args):
    """Implements the 'or' operator."""
    if any(args):
        return True
    else:
        return False


operations = {
    "if": if_,
    "and": and_,
    "or": or_,
    ">": greater,
    "gt": greater,
    "<": less,
    "lt": less,
    "<=": less_or_equal,
    ">=": greater_or_equal,
    "==": hard_equals,
}


def parse_distribution(dist_spec, rng):
    """Return a distribution described by the method policy"""
    if dist_spec["distribution"] == "gaussian":
        return rng.gaussian(dist_spec["mean"], dist_spec["std"])
    if dist_spec["distribution"] == "integers":
        return rng.integers(low=dist_spec["low"], high=dist_spec["high"])
    raise ValueError(f'Only ["gaussian", "integers"] distributions are supported, not {dist_spec["distribution"]}')


def get_variable(arg, market, rng):
    """Parse the market class to get an argument"""
    if "market" in arg:
        attr = arg.split(".")[-1]  # get the desired market attribute
        return getattr(market, attr)
    if "rand_variable" in arg:
        return parse_distribution(arg["rand_variable"], rng)
    return arg


def parse_conditional(conditional, market, rng):
    """
    Parse conditional spec

    Arguments
    ---------
    conditional : dict
        A dictionary containing a single key indicating the logic
    market : Market object
        An instantiated market object
    rng : np.random.default_rng(random_seed)
        Random number generator used in the simulation

    Returns
    -------
    bool
        The resolution of the conditional
    """

    operation = list(conditional.keys())[0]
    """
    ### TODO: 
    this operation must be one of the values in operators, defined above
    we want to recursively check each key & resolve the conditional until we get to the bottom
    we also need to check args to make sure they don't require logic ("rand_variable" or "market.*"
    """
    arg1 = get_variable(conditional["comparator"], market, rng)
    arg2 = get_variable(conditional["value"], market, rng)
    return operations["if"](arg1, arg2)


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
    action = list(action_spec)[0]
    spec = action_spec[action]
    if action == "none":
        return None
    if action == "buy":
        token_in = "base"
    elif action == "sell":
        token_in = "pt"
    else:
        raise ValueError(f'parse_json: ERROR: action_spec must be ["buy", "sell", "none"], not {action}')
    input_amount_in_usd = parse_trade_amount(spec, rng)
    return (token_in, input_amount_in_usd)


def parse_trade_amount(amount_spec, rng):
    """Return a trade amount"""
    if "method" in amount_spec:
        amount = parse_distribution(amount_spec["amount"], rng)
    else:
        amount = amount_spec["amount"]
    if amount <= 0:
        raise ValueError(f"parse_json: ERROR: amount must be >0, not {amount}.")
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

    if operator == "var":
        return get_variable(values, market, rng)
    elif operator == "amount":
        return values

    if operator not in operations:
        raise ValueError(f"Unrecognized operation {operator}")

    return operations[operator](*values)
