"""Budget class for bots"""
from __future__ import annotations

from dataclasses import dataclass

from fixedpointmath import FixedPoint, FixedPointMath

import numpy as np

from numpy.random._generator import Generator as NumpyGenerator


@dataclass
class Budget:
    rng: NumpyGenerator
    mean: float = 1
    std: float = 1
    min: float = 0
    max: float = 2

    def sample_budget():
        FixedPointMath.clip(
            self.rng.normal(loc=self.mean, scale=self.std),
            self.min,
            self.max,
        )
