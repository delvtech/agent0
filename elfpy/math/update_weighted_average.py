"""Updates a weighted average by adding or removing a weighted delta."""
from elfpy.math import FixedPoint


def update_weighted_average(
    average: FixedPoint,
    total_weight: FixedPoint,
    delta: FixedPoint,
    delta_weight: FixedPoint,
    is_adding: bool,
) -> FixedPoint:
    """Updates a weighted average by adding or removing a weighted delta.

    Arguments
    ----------
    average : FixedPoint
        The current weighted average.
    total_weight : FixedPoint
        The total aggregate weight of the average.
    delta : FixedPoint
        New value to add.
    delta_weight : FixedPoint
        The weight of the new value.
    is_adding : bool
        If the weight is added or removed to the total.

    Returns
    -------
    FixedPoint
        The new weighted average.
    """
    if is_adding:
        return (total_weight * average + delta_weight * delta) / (total_weight + delta_weight)
    if total_weight == delta_weight:
        return FixedPoint(0)
    return (total_weight * average - delta_weight * delta) / (total_weight - delta_weight)
