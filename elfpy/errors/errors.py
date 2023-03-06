"""Define Python user-defined exceptions"""


class InvalidCheckpointTime(Exception):
    """
    If the checkpoint time isn't divisible by the checkpoint duration or is in the future, it's an
    invalid checkpoint and we should revert.
    """
