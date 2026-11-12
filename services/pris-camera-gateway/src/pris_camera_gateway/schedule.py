"""The trigger instants of SOFTWARE_SCHEDULED: `k * period + delay` of the host clock."""

from __future__ import annotations

import time
from collections.abc import Callable


def normalize_delay(delay_ns: int, period_ns: int, tolerance_ns: int = 1_000) -> int:
    """Return a requested delay wrapped into [0, period).

    A delay up to `tolerance_ns` above the period counts as the period, since delays arrive as
    float32 seconds.

    Raises:
        ValueError: the period isn't positive, or the delay is outside [0, period + tolerance].
    """
    _check_period(period_ns)
    if delay_ns < 0 or delay_ns > period_ns + tolerance_ns:
        raise ValueError(f"Delay must be in [0, period], got delay_ns={delay_ns} "
                         f"and period_ns={period_ns}.")
    return delay_ns % period_ns


def rebase_delay(delay_ns: int, period_ns: int) -> int:
    """Return a delay already in use, kept inside a new period.

    Raises:
        ValueError: the period isn't positive, or the delay is negative.
    """
    _check_period(period_ns)
    if delay_ns < 0:
        raise ValueError(f"Delay must not be negative, got delay_ns={delay_ns}.")
    return delay_ns % period_ns


def next_tick(now_ns: int, period_ns: int, delay_ns: int) -> int:
    """Return the first instant `k * period + delay` strictly after `now_ns`.

    Raises:
        ValueError: the period isn't positive, or the delay is outside [0, period).
    """
    _check_period(period_ns)
    if delay_ns < 0 or delay_ns >= period_ns:
        raise ValueError(f"Delay must be in [0, period), got delay_ns={delay_ns} "
                         f"and period_ns={period_ns}.")
    k = (now_ns - delay_ns) // period_ns + 1
    return k * period_ns + delay_ns


def sleep_until(
    target_ns: int,
    clock: Callable[[], int] = time.time_ns,
    sleep: Callable[[float], None] = time.sleep,
    spin_margin_ns: int = 2_000_000,
) -> None:
    """Sleep until `spin_margin_ns` before `target_ns`, then busy-wait, since `time.sleep` may
    wake up late."""
    remaining = target_ns - clock()
    if remaining > spin_margin_ns:
        sleep((remaining - spin_margin_ns) / 1e9)
    while clock() < target_ns:
        pass


def _check_period(period_ns: int) -> None:
    if period_ns <= 0:
        raise ValueError(f"Period must be greater than zero, got period_ns={period_ns}.")
