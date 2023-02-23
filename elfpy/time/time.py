"""Core time class & utilities"""
from attr import dataclass


@dataclass
class Time:
    r"""Global time."""

    time: float = 0

    def tick(self, delta_time: float) -> None:
        """ticks the time by delta_time amount"""
        self.time += delta_time
