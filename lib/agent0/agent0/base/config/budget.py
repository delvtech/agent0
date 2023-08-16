"""Budget class for agents."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from fixedpointmath import FixedPoint, FixedPointMath
from numpy.random._generator import Generator as NumpyGenerator


@dataclass
class Budget:
    """Specifications for generating a random budget sample.

    This is used for assigning the agent's budget in base tokens.
    Wei in the variables below refers to the smallest unit of base, not to ETH.
    """

    mean_wei: int = int(5_000 * 1e18)
    std_wei: int = int(2_000 * 1e18)
    min_wei: int = int(1_000 * 1e18)
    max_wei: int = int(10_000 * 1e18)

    def sample_budget(self, rng: NumpyGenerator) -> FixedPoint:
        """Return a sample from a clipped normal distribution.

        Sample from normal distribution with mean of mean_wei and standard deviation of std_wei.
        Then clip to between a minimum of min_wei and a maximum of max_wei.

        Arguments
        ---------
        rng : NumpyGenerator
            The NumpyGenerator provides access to a wide range of distributions, and stores the random state.

        Returns
        -------
        FixedPoint
            A sample from a clipped random normal distribution according to the parameters defined at construction
        """
        return FixedPoint(
            scaled_value=FixedPointMath.clip(
                int(np.round(rng.normal(loc=self.mean_wei, scale=self.std_wei))),
                self.min_wei,
                self.max_wei,
            )
        )
