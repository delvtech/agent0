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
    "<": less,
    "<=": less_or_equal,
    ">=": greater_or_equal,
    "==": hard_equals,
}

def get_attr_from_market(market, arg):
    """Parse the market class to get an argument"""
    if "market" in arg:
        attr = arg.split(".")[1] # get the desired market attribute
        return getattr(market, attr)
    return arg

def parse_conditional(market, conditional):
    """Parse conditional spec"""
    operation = conditional["if"][0]
    arg1 = get_attr_from_market(market, conditional["if"][1])
    arg2 = get_attr_from_market(market, conditional["if"][2])
    return operations[operation](arg1, arg2)
