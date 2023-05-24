# %% [markdown]
# ## Demonstrates poisson vault apr

# pylint: disable=invalid-name

# %%
import numpy as np
from numpy.random._generator import Generator as NumpyGenerator
from scipy import special

import elfpy.utils.outputs as output_utils
from elfpy.simulators import ConfigFP
from elfpy.math import FixedPoint

# %%
vault_apr_init = 0.05  # Initial vault APR
vault_apr_jump_size = 0.05  # Scale of the vault APR change (vault_apr (+/-)= jump_size)
vault_jumps_per_year = 100  # 4 # The average number of jumps per year
vault_apr_jump_direction = "random_weighted"  # The direction of a rate change. Can be 'up', 'down', or 'random'.
vault_apr_lower_bound = 0.0  # minimum allowable vault apr
vault_apr_upper_bound = 0.06  # maximum allowable vault apr


# %%
def homogeneous_poisson(rng: NumpyGenerator, rate: float, tmax: int, bin_size: int = 1) -> np.ndarray:
    """Generate samples from a homogeneous Poisson distribution

    Attributes
    ----------
    rng: np.random.Generator
        random number generator with preset seed
    rate: float
        number of events per time interval (units of 1/days)
    tmax: float
        total number of days (units of days; sets distribution support)
    bin_size: float
        resolution of the simulation
    """
    nbins = np.floor(tmax / bin_size).astype(int)
    prob_of_spike = rate * bin_size
    events = (rng.random(nbins) < prob_of_spike).astype(int)
    return events


def event_generator(rng, n_trials, rate, tmax, bin_size):
    """Generate samples from the poisson distribution"""
    for i in range(n_trials):
        yield homogeneous_poisson(rng, rate, tmax, bin_size)


def poisson_prob(k, lam):
    """https://en.wikipedia.org/wiki/Poisson_distribution"""
    return lam**k / special.factorial(k) * np.exp(-lam)


def vault_flip_probs(apr: float, min_apr: float = 0.0, max_apr: float = 1.0, num_flip_bins: int = 100):
    """
    probability of going up is 1 when apr is min
    probability of going down is 1 when apr is max
    probability is 0.5 either way when apr is half way between max and min
    """
    aprs = np.linspace(min_apr, max_apr, num_flip_bins)

    def get_index(value, array):
        return (np.abs(array - value)).argmin()

    apr_index = get_index(apr, aprs)  # return whatever value in aprs array that apr is closest to
    up_probs = np.linspace(1, 0, num_flip_bins)
    up_prob = up_probs[apr_index]
    down_prob = 1 - up_prob
    return down_prob, up_prob


def poisson_vault_apr(
    rng: NumpyGenerator,
    num_trading_days: int,
    initial_apr: float,
    jump_size: float,
    vault_jumps_per_year: int,
    direction: str,
    lower_bound: float = 0.0,
    upper_bound: float = 1.0,
    num_flip_bins: int = 100,
) -> list:
    # vault rate changes happen once every vault_jumps_per_year, on average
    num_bins = 365
    bin_size = 1
    rate = vault_jumps_per_year / num_bins
    tmax = num_bins
    do_jump = homogeneous_poisson(rng, rate, tmax, bin_size)
    vault_apr = np.array([initial_apr] * num_trading_days)
    for day in range(1, num_trading_days):
        if not do_jump[day]:
            continue
        if direction == "up":
            sign = 1
        elif direction == "down":
            sign = -1
        elif direction == "random":
            sign = rng.choice([-1, 1], size=1).item()  # flip a fair coin
        elif direction == "random_weighted":
            probs = vault_flip_probs(vault_apr[day], lower_bound, upper_bound, num_flip_bins)
            sign = rng.choice([-1, 1], p=probs, size=1).item()  # flip a weighted coin
        else:
            raise ValueError(f"Direction must be 'up', 'down', 'weighted_random', or 'random'; not {direction}")
        step = sign * jump_size
        apr = np.minimum(upper_bound, np.maximum(lower_bound, vault_apr[day] + step))
        vault_apr[day:] = apr
    return vault_apr


# %%
fig, axs, gridspec = output_utils.get_gridspec_subplots(nrows=3, ncols=2, hspace=0.5, wspace=0.4)

tmp_config = ConfigFP()
tmp_config.num_trading_days: int = 365

n_trials = 1
num_bins = 365  # days in a year
bin_size = 1
total_num_jumps = 4  # same as vault_jumps_per_year in sim
rate = total_num_jumps / num_bins
tmax = num_bins
events_poisson = list(event_generator(tmp_config.rng, n_trials, rate, tmax, bin_size))[0]
time = np.arange(len(events_poisson))
axs[0].plot(time, events_poisson)
axs[0].set_title("events")
axs[0].set_xlabel("time (days)")
axs[0].set_yticks([0, 1])

n_trials = 100000
n_events = np.array([np.sum(events) for events in event_generator(tmp_config.rng, n_trials, rate, tmax, bin_size)])
bin_edges = np.arange(n_events.max() + 1) - 0.5
lam = rate * tmax
k = bin_edges + 0.5
prob = poisson_prob(k, lam)
axs[1].hist(n_events, bin_edges, density=True, fc="none", ec="k")
axs[1].plot(k, prob, c="b")
axs[1].set_title("event probability")
axs[1].set_xlabel(f"number of events in {tmax} days")
axs[1].set_ylabel(f"probability")

num_flip_bins = 1000
aprs = np.linspace(vault_apr_lower_bound, vault_apr_upper_bound, num=num_flip_bins)
probs = [vault_flip_probs(apr, vault_apr_lower_bound, vault_apr_upper_bound, num_flip_bins) for apr in aprs]
down_probs = [prob[0] for prob in probs]
up_probs = [prob[1] for prob in probs]
axs[2].plot(aprs, down_probs, c="b", label="jump down")
axs[2].plot(aprs, up_probs, c="r", label="jump up")
axs[2].set_title("APR probabilities")
axs[2].set_xlabel("vault APR")
axs[2].set_ylabel("probability weighting")
axs[2].legend()

initial_apr = 0.5
jump_size = 0.01
num_jumps = 4
upper_bound = 100
lower_bound = -100
vault_apr = poisson_vault_apr(
    rng=tmp_config.rng,
    num_trading_days=tmp_config.num_trading_days,
    initial_apr=initial_apr,
    jump_size=jump_size,
    vault_jumps_per_year=num_jumps,
    direction="random",
    lower_bound=lower_bound,
    upper_bound=upper_bound,
    num_flip_bins=num_flip_bins,
)
axs[3].plot(np.arange(tmp_config.num_trading_days), vault_apr, c="k")
axs[3].set_xlabel("time (days)")
axs[3].set_ylabel("poisson process")
axs[3].set_title("random unweighted")

initial_apr = 0.5
jump_size = 0.01
num_jumps = 4
lower_bound = 0.4  # use new values to demonstrate how bounds work with random weights
upper_bound = 0.6
vault_apr = poisson_vault_apr(
    rng=tmp_config.rng,
    num_trading_days=tmp_config.num_trading_days,
    initial_apr=initial_apr,
    jump_size=jump_size,
    vault_jumps_per_year=num_jumps,
    direction="random_weighted",
    lower_bound=lower_bound,
    upper_bound=upper_bound,
    num_flip_bins=num_flip_bins,
)
axs[4].plot(np.arange(tmp_config.num_trading_days), vault_apr, c="k")
axs[4].plot([0, tmp_config.num_trading_days - 1], [lower_bound, lower_bound], c="r", linewidth=0.5)
axs[4].plot([0, tmp_config.num_trading_days - 1], [upper_bound, upper_bound], c="r", linewidth=0.5)
axs[4].set_xlabel("time (days)")
axs[4].set_ylabel("poisson process")
axs[4].set_title(f"random weighted\n(avg {num_jumps} jumps)")
axs[4].set_ylim([lower_bound - 0.05, upper_bound + 0.05])

vault_apr = poisson_vault_apr(
    rng=tmp_config.rng,
    num_trading_days=tmp_config.num_trading_days,
    initial_apr=initial_apr,
    jump_size=jump_size,
    vault_jumps_per_year=num_jumps * 10,
    direction="random_weighted",
    lower_bound=lower_bound,
    upper_bound=upper_bound,
    num_flip_bins=num_flip_bins,
)
axs[5].plot(np.arange(tmp_config.num_trading_days), vault_apr, c="k")
axs[5].plot([0, tmp_config.num_trading_days - 1], [lower_bound, lower_bound], c="r", linewidth=0.5)
axs[5].plot([0, tmp_config.num_trading_days - 1], [upper_bound, upper_bound], c="r", linewidth=0.5)
axs[5].set_xlabel("time (days)")
axs[5].set_ylabel("poisson process")
axs[5].set_title(f"random weighted\n(avg {num_jumps * 10} jumps)")
axs[5].set_ylim([lower_bound - 0.05, upper_bound + 0.05])


fig_w = 6
fig_h = fig_w * 3 / 2
fig.set_size_inches((fig_w, fig_h))

# %%
