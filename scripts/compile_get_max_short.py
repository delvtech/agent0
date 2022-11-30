import numpy as np

from elfpy.pricing_models import HyperdrivePricingModel
import elfpy.utils.get_max_short as utils

# NOTE: Some of these constants will need to be swept over.
init_share_price = 1
share_price = 1
days_remaining = 182.5
fee_percent = 0.1

# We always use the Hyperdrive pricing model for compilation.
model = HyperdrivePricingModel()

# Sweep over a large range of APRs to compute the approximations.
raw_approximations = {}
for apr in utils.calc_chebyshev_nodes(0, 2, 50):
    time_stretch = model.calc_time_stretch(apr)

    # TODO: Don't use normalize percents by multiplying things by 100. It just
    # makes things more annoying.
    #
    # Calculate the maximum bond percentage that doesn't result in an invalid max loss.
    (max_max_loss_percentage, max_bond_percentage) = utils.calc_max_loss_endpoints(
        model, apr, share_price, init_share_price, fee_percent, days_remaining, time_stretch
    )

    # Capture an array of max losses (the x component) and the bond ratios (the y component)
    # that require the max losses.
    y = utils.calc_chebyshev_nodes(0, max_bond_percentage, 100)
    x = (
        utils.calc_max_loss_from_apr(
            model, y, apr, share_price, init_share_price, fee_percent, days_remaining, time_stretch
        )
        / utils.SHARE_RESERVES
    )

    # Construct a new trace of sample data to test for the error
    y_test = np.delete(np.arange(0, max_bond_percentage, 0.001), 0)
    x_test = (
        utils.calc_max_loss_from_apr(
            model, y_test, apr, share_price, init_share_price, fee_percent, days_remaining, time_stretch
        )
        / utils.SHARE_RESERVES
    )

    # Fit a rational curve to the data points.
    (num_degree, popt) = utils.ratfit(x, y, x_test, y_test, start_degree=1, end_degree=20)
    approx = utils.construct_get_max_short_approximation(num_degree, popt, max_max_loss_percentage, max_bond_percentage)
    min_error = abs(np.amin(y_test - approx(x_test)))
    raw_approximations[apr] = (num_degree, popt.tolist(), max_max_loss_percentage, max_bond_percentage, min_error)

# Write the approximations to a file.
utils.write_approximations(raw_approximations)
