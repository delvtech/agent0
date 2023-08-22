def build_fixed_rate(pool_analysis):
    fixed_rate = pool_analysis[["timestamp", "fixed_rate"]]
    return fixed_rate
