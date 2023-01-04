# test 1: 5M target_liquidity; 5% APR;
#   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
#   1 init share price; 1 share price
l = target_liquidity = 5_000_000
r = target_apr = 0.05
days = 182.5
time_stretch = 3.09396 / (0.02789 * r * 100)
t = days / 365
T = t / time_stretch
u = init_share_price = 1
c = share_price = 1  # share price of the LP in the yield source; c = 1
z = share_reserves = l / c
y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
p = ((2 * y + c * z) / (u * z)) ** (-T)  # spot price from reserves
final_apr = (1 - p) / (p * t)
total_liquidity = c * z
print(
    "\ntest 1:"
    f"\n\t{target_liquidity=}"
    f"\n\t{target_apr=}"
    f"\n\t{days=}"
    f"\n\t{time_stretch=}"
    f"\n\t{init_share_price=}"
    f"\n\t{share_price=}"
    f"\n\texpected_share_reserves={z}"
    f"\n\texpected_bond_reserves={y}"
    f"\n\t{final_apr=}"
    f"\n\t{total_liquidity=}"
)


# test 2: 5M target_liquidity; 2% APR;
#   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
#   1 init share price; 1 share price
l = target_liquidity = 5_000_000
r = target_apr = 0.02
days = 182.5
time_stretch = 3.09396 / (0.02789 * r * 100)
t = days / 365
T = t / time_stretch
u = init_share_price = 1
c = share_price = 1  # share price of the LP in the yield source; c = 1
z = share_reserves = l / c
y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
p = ((2 * y + c * z) / (u * z)) ** (-T)
final_apr = (1 - p) / (p * t)
total_liquidity = c * z
print(
    "\ntest 2:"
    f"\n\t{target_liquidity=}"
    f"\n\t{target_apr=}"
    f"\n\t{days=}"
    f"\n\t{time_stretch=}"
    f"\n\t{init_share_price=}"
    f"\n\t{share_price=}"
    f"\n\texpected_share_reserves={z}"
    f"\n\texpected_bond_reserves={y}"
    f"\n\t{final_apr=}"
    f"\n\t{total_liquidity=}"
)


# test 3: 5M target_liquidity; 8% APR;
#   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
#   1 init share price; 1 share price
l = target_liquidity = 5_000_000
r = target_apr = 0.08
days = 182.5
time_stretch = 3.09396 / (0.02789 * r * 100)
t = days / 365
T = t / time_stretch
u = init_share_price = 1
c = share_price = 1  # share price of the LP in the yield source; c = 1
z = share_reserves = l / c
y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
p = ((2 * y + c * z) / (u * z)) ** (-T)
final_apr = (1 - p) / (p * t)
total_liquidity = c * z
print(
    "\ntest 3:"
    f"\n\t{target_liquidity=}"
    f"\n\t{target_apr=}"
    f"\n\t{days=}"
    f"\n\t{time_stretch=}"
    f"\n\t{init_share_price=}"
    f"\n\t{share_price=}"
    f"\n\texpected_share_reserves={z}"
    f"\n\texpected_bond_reserves={y}"
    f"\n\t{final_apr=}"
    f"\n\t{total_liquidity=}"
)

# test 4:  10M target_liquidity; 3% APR
#   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
#   1.5 init share price; 2 share price
l = target_liquidity = 10_000_000
r = target_apr = 0.03
days = 91.25
time_stretch = 3.09396 / (0.02789 * r * 100)
t = days / 365
T = t / time_stretch
u = init_share_price = 1.5
c = share_price = 2  # share price of the LP in the yield source; c = 1
z = share_reserves = l / c
y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
p = ((2 * y + c * z) / (u * z)) ** (-T)
final_apr = (1 - p) / (p * t)
total_liquidity = c * z
print(
    "\ntest 4:"
    f"\n\t{target_liquidity=}"
    f"\n\t{target_apr=}"
    f"\n\t{days=}"
    f"\n\t{time_stretch=}"
    f"\n\t{init_share_price=}"
    f"\n\t{share_price=}"
    f"\n\texpected_share_reserves={z}"
    f"\n\texpected_bond_reserves={y}"
    f"\n\t{final_apr=}"
    f"\n\t{total_liquidity=}"
)

# test 5:  10M target_liquidity; 5% APR
#   9mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
#   1.5 init share price; 2 share price
l = target_liquidity = 10_000_000
r = target_apr = 0.03
days = 273.75
time_stretch = 3.09396 / (0.02789 * r * 100)
t = days / 365
T = t / time_stretch
u = init_share_price = 1.3
c = share_price = 1.5  # share price of the LP in the yield source; c = 1
z = share_reserves = l / c
y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
p = ((2 * y + c * z) / (u * z)) ** (-T)
final_apr = (1 - p) / (p * t)
total_liquidity = c * z
print(
    "\ntest 5:"
    f"\n\t{target_liquidity=}"
    f"\n\t{target_apr=}"
    f"\n\t{days=}"
    f"\n\t{time_stretch=}"
    f"\n\t{init_share_price=}"
    f"\n\t{share_price=}"
    f"\n\texpected_share_reserves={z}"
    f"\n\texpected_bond_reserves={y}"
    f"\n\t{final_apr=}"
    f"\n\t{total_liquidity=}"
)
