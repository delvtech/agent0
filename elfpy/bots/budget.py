"""Budget class for bots."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from fixedpointmath import FixedPoint, FixedPointMath
from numpy.random._generator import Generator as NumpyGenerator


@dataclass
class Budget:
    """Specifications for generating a random budget sample."""

    mean_wei: int = int(1e18)  # 1 ETH
    std_wei: int = int(1e17)  # 0.1 ETH
    min_wei: int = 1  # 1 WEI
    max_wei: int = int(1e21)  # 1k ETH

    def sample_budget(self, rng: NumpyGenerator) -> FixedPoint:
        """Return a sample from a clipped normal distribution.

        Sample from normal distribution with mean of mean_wei and standard deviation of std_wei.
        Then clip to between a minimum of min_wei and a maximum of max_wei.

        Arguments
        ---------
        rng : NumpyGenerator
            Random number generator

        Returns
        -------
        FixedPoint
            The resulting sample
        """
        return FixedPoint(
            scaled_value=FixedPointMath.clip(
                int(np.round(rng.normal(loc=self.mean_wei, scale=self.std_wei))),
                self.min_wei,
                self.max_wei,
            )
        )
