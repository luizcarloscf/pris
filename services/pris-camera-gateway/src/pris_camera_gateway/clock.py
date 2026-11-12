"""The camera's timestamp counter mapped to the host clock."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import NamedTuple


class LatchSample(NamedTuple):
    """One latch of the camera counter, between two readings of the host clock."""

    host_before_ns: int
    camera_ticks: int
    host_after_ns: int

    @property
    def round_trip_ns(self) -> int:
        return self.host_after_ns - self.host_before_ns


class ClockMapper(object):
    """Maps the camera timestamp counter to the host clock.

    Each `update` keeps the sample of a burst with the shortest round trip, the least delayed
    by the latch command, and pairs its camera time with the middle of its host readings. The
    camera clock drifts against the host's, so the mapping is a line fitted over the last
    `window` pairs; a counter that goes backwards (a camera reset) starts the fit again.
    """

    def __init__(self, ns_per_tick: float, window: int = 10) -> None:
        """
        Args:
            ns_per_tick: nanoseconds per tick of the camera counter.
            window: the pairs the line is fitted over.

        Raises:
            ValueError: `ns_per_tick` isn't positive or `window` is below 1.
        """
        if ns_per_tick <= 0:
            raise ValueError(f"ns_per_tick must be greater than zero, got {ns_per_tick}.")
        if window < 1:
            raise ValueError(f"window must be at least 1, got {window}.")
        self._ns_per_tick = ns_per_tick
        self._points: deque[tuple[int, int]] = deque(maxlen=window)
        self._slope = 1.0

    @property
    def ready(self) -> bool:
        """Whether a sample was received, so `to_host_ns` can map."""
        return len(self._points) > 0

    @property
    def drift_ppm(self) -> float:
        """The camera clock's drift against the host's, in parts per million."""
        return (self._slope - 1.0) * 1e6

    def update(self, samples: Sequence[LatchSample]) -> None:
        """Add the best sample of a burst to the fit.

        Raises:
            ValueError: `samples` is empty.
        """
        if len(samples) == 0:
            raise ValueError("At least one latch sample is required.")
        best = min(samples, key=lambda sample: sample.round_trip_ns)
        camera_ns = round(best.camera_ticks * self._ns_per_tick)
        host_ns = (best.host_before_ns + best.host_after_ns) // 2
        if len(self._points) > 0 and camera_ns <= self._points[-1][0]:
            self._points.clear()
        self._points.append((camera_ns, host_ns))
        self._slope = self._fit_slope()

    def to_host_ns(self, camera_ticks: int) -> int:
        """Return the host time of a camera counter value.

        Raises:
            RuntimeError: no sample was received yet.
        """
        if not self.ready:
            raise RuntimeError("ClockMapper has no samples yet, call update first.")
        ref_camera_ns, ref_host_ns = self._points[-1]
        camera_ns = camera_ticks * self._ns_per_tick
        return ref_host_ns + round((camera_ns - ref_camera_ns) * self._slope)

    def _fit_slope(self) -> float:
        if len(self._points) < 2:
            return 1.0
        # * centered on the last point: absolute host times (~1e18 ns) would lose float precision
        ref_camera_ns, ref_host_ns = self._points[-1]
        xs = [camera_ns - ref_camera_ns for camera_ns, _ in self._points]
        ys = [host_ns - ref_host_ns for _, host_ns in self._points]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        sxx = sum((x - mean_x)**2 for x in xs)
        if sxx == 0:
            return 1.0
        sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        return sxy / sxx
