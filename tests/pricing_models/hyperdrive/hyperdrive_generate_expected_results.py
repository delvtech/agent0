# pylint: skip-file


def calc_in_given_out(token_out, test_id):
    ## time calculations

    # t(d) = days_remaining / 365 or just time_remaining in years, t
    t = t_d = d / 365
    # from base.py
    t_stretch = 3.09396 / (0.02789 * (r * 100))
    tau = t_d / t_stretch

    z = share_reserves
    y = bond_reserves

    if token_out == "base":
        z -= out * (1 - t) / c
        y += out * (1 - t)
    elif token_out == "pt":
        z += out * (1 - t) / c
        y -= out * (1 - t)

    ## output calculations
    # in = curve + flat
    # curve = c * ((1 / u) * ((k - (2 * y + c * z - delta_y * tau) ** (1 - tau)) / (c / u)) ** (1 / (1 - tau)) - z)
    # flat = delta_y * (1 - t)

    # in the curve part of the equation, we pass the full time remaining so that we are always
    # trading on the same curve to prevent sandwhich attacks via curve hopping
    t_full = 1
    tau_full = t_full / t_stretch

    ## amm constants
    k = (c / u) * (u * z) ** (1 - tau_full) + (2 * y + c * z) ** (1 - tau_full)
    ## from base.py
    p = spot_price = ((2 * y + c * z) / (u * z)) ** -tau_full

    # if token_out is base:
    #   yield space equation: (for hyperdrive multiply d_z by t)
    #   (c / μ) * (μ * (z - d_z))**(1 - tau) + (2y + cz + d_y')**(1 - tau) = k
    #   d_y' = (k - (c / μ) * (μ * (z - d_z))**(1 - tau))**(1 / (1 - tau)) - (2y + cz)
    in_pt = (
        # curve (note: use delta_z * t to phase the curve part out, and delta_z * (1 - t)
        # to phase the flat part in over the length of the term.
        # curve out and flat in over time)
        (k - (c / u) * (u * (z - delta_z * t)) ** (1 - tau_full)) ** (1 / (1 - tau_full))
        - (2 * y + c * z)
        # flat uses t (time remaining)
        + c * delta_z * (1 - t)
    )

    # if token_out is pt:
    #   yield space equation: (for hyperdrive multiply d_y by t)
    #   (c / μ) * (μ * (z + d_z'))**(1 - tau) + (2y + cz - d_y)**(1 - tau) = k
    #   d_z' = (1 / μ) * ((k - (2y + cz - d_y)**(1 - tau)) / (c / μ))**(1 / (1 - tau)) - z
    #   d_x' = c * d_z', x = cz
    #   d_x' = c*(1 / μ) * ((k - (2y + cz - d_y)**(1 - tau)) / (c / μ))**(1 / (1 - tau)) - z
    in_base = (
        # curve (note: delta_y * t to phase out curve part)
        c * ((1 / u) * ((k - (2 * y + c * z - delta_y * t) ** (1 - tau_full)) / (c / u)) ** (1 / (1 - tau_full)) - z)
        # flat (note: delta_y * (t - 1) to phase in flat part)
        + delta_y * (1 - t)
    )

    if token_out == "base":
        without_fee_or_slippage = (
            # 'curve' part, but not really, just spot price.  again note the use of t_full for the
            # curve part of the equation
            (1 / p) * c * delta_z * t
            # flat part
            + c * delta_z * (1 - t)
        )
        # normal flat + curve equation, includes slippage
        without_fee = in_pt
        fee = (((2 * y + c * z) / (u * z)) ** tau_full - 1) * phi * c * delta_z * t
        with_fee = in_pt + fee
    else:  # token_out == 'pt'
        without_fee_or_slippage = (
            # 'curve' part, but not really, just spot price.  again note the use of t_full for the
            # curve part of the equation
            p * delta_y * t_full
            # flat part
            + delta_y * (1 - t)
        )
        # normal flat + curve equation, includes slippage
        without_fee = in_base
        fee = (1 - (1 / ((2 * y + c * z) / (u * z)) ** tau_full)) * phi * delta_y * t
        with_fee = in_base + fee

    print(
        (
            f"                # {t_d=}\n"
            f"                # {tau=}\n"
            f"                # {1-tau=}\n"
            f"                # {t_stretch=}\n"
            f"                # {spot_price=}\n"
            f"                TestCaseCalcInGivenOutSuccess(\n"
            f"                    out=Quantity(amount={delta_y}, unit=TokenType.{token_out.upper()}),\n"
            f"                    market_state=MarketState(\n"
            f"                        share_reserves={share_reserves},  # base reserves (in share terms) base = share * share_price\n"
            f"                        bond_reserves={bond_reserves},  # PT reserves\n"
            f"                        share_price={share_price},  # share price of the LP in the yield source\n"
            f"                        init_share_price={init_share_price},  # original share price pool started\n"
            f"                    ),\n"
            f"                    fee_percent={phi},  # fee percent (normally 10%)\n"
            f"                    days_remaining={d},  # {d / 365 * 12} months remaining\n"
            f"                    time_stretch_apy={r},  # APY used to calculate time_stretch\n"
            f"                    {test_id=},\n"
            f"                ),\n"
            f"                # {in_base=}\n"
            f"                # {in_pt=}\n"
            f"                TestResultCalcInGivenOutSuccess(\n"
            f"                    {without_fee_or_slippage=},\n"
            f"                    {without_fee=},\n"
            f"                    hyperdrive_{fee=},\n"
            f"                    hyperdrive_{with_fee=},\n"
            f"                ),"
        )
    )


def run_it(func, test_number):
    token = "base"
    print(f"            (  # test {test_number}, token {token.upper()}")
    func(token, test_number)
    print(f"            ),  # end of test {test_number}")

    # token = "pt"
    # print(f"            (  # test {test_number}, token {token.upper()}")
    # func(token, test_number)
    # print(f"            ),  # end of test {test_number}")


####################
####################
# IN GIVEN OUT
####################
####################

# 1. out = 100; 10% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining;
phi = fee = 0.1
z = share_reserves = 100_000
y = bond_reserves = 100_000
c = share_price = 1
u = init_share_price = 1
r = pool_apy = 0.05  # this apy should be used to calculate the time stretch
d = 6 * 365 / 12  # days remaining
delta_y = delta_x = out = 100  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 1)

# 2. out = 100; 20% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
phi = fee = 0.2
z = share_reserves = 100_000
y = bond_reserves = 100_000
c = share_price = 1
u = init_share_price = 1
r = pool_apy = 0.05
d = 6 * 365 / 12  # days remaining
delta_y = delta_x = out = 100  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 2)

# 3. out = 10k; 10% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
phi = fee = 0.1
z = share_reserves = 100_000
y = bond_reserves = 100_000
c = share_price = 1
u = init_share_price = 1
r = pool_apy = 0.05
d = 6 * 365 / 12  # days remaining
delta_y = delta_x = out = 10_000  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 3)


# 4. out = 80k; 10% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
phi = fee = 0.1
z = share_reserves = 100_000
y = bond_reserves = 100_000
c = share_price = 1
u = init_share_price = 1
r = pool_apy = 0.05
d = 6 * 365 / 12  # days remaining
delta_y = delta_x = out = 80_000  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 4)


# 5. out = 200; 10% fee; 100k share reserves; 100k bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
phi = fee = 0.1
z = share_reserves = 100_000
y = bond_reserves = 100_000
c = share_price = 2
u = init_share_price = 1.5
r = pool_apy = 0.05
d = 6 * 365 / 12  # days remaining
delta_y = delta_x = out = 200  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 5)


# 6. out = 200; 10% fee; 100k share reserves; 1M bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
phi = fee = 0.1
z = share_reserves = 100_000
y = bond_reserves = 1_000_000
c = share_price = 2
u = init_share_price = 1.5
r = pool_apy = 0.05
d = 6 * 365 / 12  # days remaining
delta_y = delta_x = out = 200  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 6)


# 7. out = 200; 10% fee; 100k share reserves; 1M bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
#    3 mo remaining
phi = fee = 0.1
z = share_reserves = 100_000
y = bond_reserves = 1_000_000
c = share_price = 2
u = init_share_price = 1.5
r = pool_apy = 0.05
d = 3 * 365 / 12  # days remaining
delta_y = delta_x = out = 200  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 7)


# 8. out = 200; 10% fee; 100k share reserves; 1M bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 10% APY;
#    3 mo remaining
delta_y = delta_z = out = 200  # same amount regardless of units
phi = fee = 0.1
z = share_reserves = 100_000
y = bond_reserves = 1_000_000
c = share_price = 2
u = init_share_price = 1.5
r = pool_apy = 0.10
d = 3 * 365 / 12  # days remaining
delta_y = delta_x = out = 200  # same amount regardless of units
delta_z = delta_x / c
run_it(calc_in_given_out, 8)
