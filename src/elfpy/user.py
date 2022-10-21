"""
Implements abstract classes that control user behavior
"""

import numpy as np
from scipy.stats import binomtest


class User:
    """
    Implements abstract classes that control user behavior
    """

    def __init__(self, **kwargs):
        """Nothing to initialize"""

    @staticmethod
    def random_direction(rng):
        """Picks random direction"""
        return rng.integers(low=0, high=2)  # 0 or 1

    @staticmethod
    def stochastic_direction(
        pool_apy,
        pool_apy_target_range,
        days_trades,
        pool_apy_target_range_convergence_speed,
        rng,
        run_trade_number,
        verbose=False,
    ):
        """Picks p-value-weighted direction, cutting off tails"""
        # pylint: disable=too-many-arguments
        btest = []
        expected_proportion = 0
        streak_luck = 0
        apy_distance_in_target_range = np.clip(
            (pool_apy - pool_apy_target_range[0]) / (pool_apy_target_range[1] - pool_apy_target_range[0]),
            0,
            1,
        )
        convergence_direction = (
            0 if apy_distance_in_target_range > 0.5 else 1
        )  # if you're above the midpoint of the targe range
        apy_distance_from_mid_when_in_range = np.clip(
            np.abs(apy_distance_in_target_range - 0.5) * 2, 0, 1
        )  # 0 if you're at the midpoint, 1 if you're at the edge
        actual_convergence_strength = (
            0.5 + (pool_apy_target_range_convergence_speed - 0.5) * apy_distance_from_mid_when_in_range
        )  # pool_apy_target_range_convergence_speed at edge or outside, scales to 0 at midpoint
        expected_proportion = (
            actual_convergence_strength if convergence_direction == 1 else 1 - actual_convergence_strength
        )
        if len(days_trades) > 0:
            btest = binomtest(
                k=sum(days_trades),
                n=len(days_trades),
                p=expected_proportion,
            )
            streak_luck = 1 - btest.pvalue
        if streak_luck > 0.98 and verbose:
            token_index = 1 - round(sum(days_trades) / len(days_trades))
            print(
                "trade"
                f" {run_trade_number}"
                f" days_trades={days_trades}+{token_index}k={sum(days_trades)}"
                f" n={len(days_trades)} ratio={sum(days_trades)/len(days_trades)}"
                f" streak_luck: {streak_luck}"
            )
        else:
            if 0 < apy_distance_from_mid_when_in_range < 1:
                actual_convergence_strength = (
                    actual_convergence_strength + (1 - actual_convergence_strength) * streak_luck**1.5
                )  # force convergence when on bad streaks
            token_index = (
                convergence_direction if rng.random() < actual_convergence_strength else 1 - convergence_direction
            )
        return (token_index,apy_distance_in_target_range,apy_distance_from_mid_when_in_range,
            actual_convergence_strength,expected_proportion,streak_luck,btest)
