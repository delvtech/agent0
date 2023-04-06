"""Updates a weighted average by adding or removing a weighted delta."""


def update_weighted_average(
    average: float,
    total_weight: float,
    delta: float,
    delta_weight: float,
    is_adding: bool,
) -> float:
    """Updates a weighted average by adding or removing a weighted delta.

    Parameters
    ----------
    average: float
        The current weighted average.
    total_weight: float
        The total aggregate weight of the average.
    delta: float
        New value to add.
    delta_weight: float
        The weight of the new value.
    is_adding: bool
        If the weight is added or removed to the total.

    Returns
    -------
    float
        The new weighted average.
    """

    if is_adding:
        return (total_weight * average + delta_weight * delta) / (total_weight + delta_weight)
    if total_weight == delta_weight:
        return 0
    return (total_weight * average - delta_weight * delta) / (total_weight - delta_weight)
