import json
import numpy as np
import os
from pathlib import Path
import scipy

from elfpy.pricing_models import PricingModel
import elfpy.utils.price as price_utils
import elfpy.utils.time as time_utils


# The project root.
ROOT = Path(__file__).parent.parent.parent.parent
APPROXIMATIONS_PATH = f"{ROOT}/generated/get_max_short_approximations.json"
# NOTE: The actual share reserves are completely arbitrary since we do all of
#       our approximations on reserve ratios.
SHARE_RESERVES = 10e6


def calc_max_loss_from_apr(
    pricing_model: PricingModel,
    bond_percentage,
    apr,
    share_price,
    init_share_price,
    fee_percent,
    days_remaining,
    time_stretch,
):
    """
    Calculates the maximum loss on a short position of a specified percentage of the total bond reserves
    """
    time_remaining = time_utils.stretch_time(time_utils.norm_days(days_remaining), time_stretch)
    bond_reserves = price_utils.calc_bond_reserves(
        SHARE_RESERVES,
        apr,
        days_remaining,
        time_stretch,
        share_price,
        init_share_price,
    )
    d_bonds = bond_reserves * bond_percentage
    try:
        d_shares = pricing_model.calc_in_given_out(
            d_bonds,
            SHARE_RESERVES,
            bond_reserves,
            "base",
            fee_percent,
            time_remaining,
            share_price,
            init_share_price,
        )
    except AssertionError as e:
        if "ERROR: without_fee should be non-negative, not nan!" in f"{e}":
            return np.NaN
        raise e
    return d_bonds - d_shares


def calc_max_loss_endpoints(
    pricing_model: PricingModel,
    apr,
    share_price,
    init_share_price,
    fee_percent,
    days_remaining,
    time_stretch,
):
    """Find the maximum bond percentage that doesn't cause a max loss of NaN using the bisection method"""
    last_valid_max_loss_percentage = 0
    last_valid_bond_percentage = 0
    bond_percentage = 1
    max_loss = calc_max_loss_from_apr(
        pricing_model,
        bond_percentage,
        apr,
        share_price,
        init_share_price,
        fee_percent,
        days_remaining,
        time_stretch,
    )
    if not (isinstance(max_loss, complex) or np.isnan(max_loss)):
        return (max_loss / SHARE_RESERVES, bond_percentage)
    for step_size in [1 / (2 ** (x + 1)) for x in range(0, 25)]:
        if isinstance(max_loss, complex) or np.isnan(max_loss):
            bond_percentage -= step_size
        else:
            last_valid_max_loss_percentage = max_loss / SHARE_RESERVES
            last_valid_bond_percentage = bond_percentage
            bond_percentage += step_size
        max_loss = calc_max_loss_from_apr(
            pricing_model,
            bond_percentage,
            apr,
            share_price,
            init_share_price,
            fee_percent,
            days_remaining,
            time_stretch,
        )
    return (last_valid_max_loss_percentage, last_valid_bond_percentage)


def calc_chebyshev_nodes(start, end, num_points):
    """Create a set of Chebyshev nodes to use for approximation routines"""
    i = np.delete(np.arange(num_points + 1), 0)
    return ((start + end) / 2) + ((start - end) / 2) * np.cos(((2 * i) / (2 * num_points)) * np.pi)


def ratobj(num_degree):
    """
    Returns generic n-th degree rational objective function that can be used with
    SciPy's `curvefit` function to approximate a set of data points.
    """
    return lambda x, *coeffs: np.polyval(coeffs[:num_degree], x) / (1 + np.polyval(coeffs[num_degree:], x) * x)


def ratfit(xdata, ydata, xtest, ytest, start_degree=2, end_degree=10, verbose=False):
    """
    Finds the rational polynomial that minimizes the maximum error up to the given degree.
    """
    min_error = float("inf")
    min_num_degree = 1
    min_popt = np.ones(1)
    # Compute the least squares optimal rational polynomial over all of the possible degrees
    for degree in range(start_degree, end_degree + 1):
        for div_degree in range(0, degree):
            num_degree = degree - div_degree
            try:
                # Compute the optimal parameters
                p0 = tuple(np.ones(degree))
                popt, _ = scipy.optimize.curve_fit(ratobj(num_degree), xdata, ydata, p0=p0)
                # Compute the error and the maximum error with the objective function
                error = ytest - ratobj(num_degree)(xtest, *popt)
                error = max(np.amax(error), np.abs(np.amin(error)))
                if verbose:
                    print(f"num_degree = {num_degree} & div_degree = {div_degree}")
                    print(f"error = {error} & min_error = {min_error}")
                if error < min_error:
                    if verbose:
                        print(f"updated best fit")
                    min_error = error
                    min_num_degree = num_degree
                    min_popt = popt
            except RuntimeError as e:
                if verbose:
                    print(f"ratfit: curve fitting failed for ({num_degree}, {div_degree}) rational with: {e}")
    return (min_num_degree, min_popt)


def construct_get_max_short_approximation(
    num_degree, popt, max_max_loss_percentage, max_bond_percentage, correction=0.0
):
    """
    Constructs a function for a given set of parameters that maps from an amount
    of base to the maximum amount that can be shorted for that base.
    """
    return lambda x: np.piecewise(
        x,
        [x <= max_max_loss_percentage, x > max_max_loss_percentage],
        [lambda y: ratobj(num_degree)(y, *popt) + correction, lambda _: max_bond_percentage],
    )


def get_max_short_weighted_mean(base, apr, approximation_idx, approximations):
    """
    Computes the maximum short possible for a specified base amount given a mesh
    of approximation functions by taking the minimum of the closest curves.
    """
    near_idx = (np.abs(approximation_idx - apr)).argmin()
    near = approximation_idx[near_idx]
    if near_idx == approximation_idx.size - 1 and apr > near:
        raise Exception(f"get_max_short_weighted_mean: expected apr <= {near}, not {apr}!")
    if apr == near or (near_idx == 0 and apr < near) or (near_idx == approximation_idx.size - 1 and apr > near):
        return approximations[near](base)
    elif apr > near:
        far = approximation_idx[near_idx + 1]
    else:
        far = approximation_idx[near_idx - 1]
    near_weight = 1 - (abs(near - apr) / abs(near - far))
    far_weight = 1 - (abs(far - apr) / abs(near - far))
    return near_weight * approximations[near](base) + far_weight * approximations[far](base)


def get_max_short_minimum(base, apr, approximation_idx, approximations):
    """
    Computes the maximum short possible for a specified base amount given a mesh
    of approximation functions by taking the minimum of the closest curves.
    """
    near_idx = (np.abs(approximation_idx - apr)).argmin()
    near = approximation_idx[near_idx]
    if near_idx == approximation_idx.size - 1 and apr > near:
        raise Exception(f"get_max_short_minimum: expected apr <= {near}, not {apr}!")
    if apr == near or (near_idx == 0 and apr < near) or (near_idx == approximation_idx.size - 1 and apr > near):
        return approximations[near](base)
    elif apr > near:
        far = approximation_idx[near_idx + 1]
    else:
        far = approximation_idx[near_idx - 1]
    return np.minimum(approximations[near](base), approximations[far](base))


def write_approximations(raw_approximations):
    """
    Writes a set of JSON serialized approximations to the generated/ directory
    in the project root.
    """
    # Ensure that the directory is present.
    if not os.path.exists(APPROXIMATIONS_PATH):
        os.mkdir(APPROXIMATIONS_PATH)

    # Write the approximations to the file.
    with open(APPROXIMATIONS_PATH, "w") as f:
        json.dump(approximations, f)


def read_approximations():
    """
    Reads a set of JSON serialized approximations from the generated/ directory
    in the project root.
    """
    with open(APPROXIMATIONS_PATH, "r") as f:
        raw_approximations = json.load(f)

    # Reify the approximations dictionary and construct an index that can be
    # used for interpolation.
    approximations = {}
    for (
        apr,
        (num_degree, popt_list, max_max_loss_percentage, max_bond_percentage, min_error),
    ) in raw_approximations.items():
        popt = np.array(popt_list)
        approximations[float(apr)] = construct_get_max_short_approximation(
            num_degree, popt, max_max_loss_percentage, max_bond_percentage, min_error
        )
    approximation_idx = np.sort(np.fromiter(approximations.keys(), dtype=float))

    return (approximations, approximation_idx)
