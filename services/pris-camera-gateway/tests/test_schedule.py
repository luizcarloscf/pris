import numpy as np
import pytest

from pris_camera_gateway.schedule import (
    next_tick,
    normalize_delay,
    rebase_delay,
    sleep_until,
)

MS = 1_000_000
DELAY_TOLERANCE_NS = 1_000
PERIOD = 100 * MS


@pytest.mark.parametrize(
    "now_ns,delay_ns,expected",
    [
        (0, 0, PERIOD),
        (1, 0, PERIOD),
        (PERIOD - 1, 0, PERIOD),
        # exactly on a tick: the next one is returned
        (PERIOD, 0, 2 * PERIOD),
        (0, 30 * MS, 30 * MS),
        (30 * MS, 30 * MS, PERIOD + 30 * MS),
        (50 * MS, 30 * MS, PERIOD + 30 * MS),
        (10 * PERIOD + 99 * MS, 99 * MS, 11 * PERIOD + 99 * MS),
    ],
)
def test_next_tick(now_ns, delay_ns, expected):
    assert next_tick(now_ns, PERIOD, delay_ns) == expected


def test_next_tick_wall_clock_magnitude():
    now_ns = 1_761_000_000_123_456_789
    tick = next_tick(now_ns, PERIOD, 7 * MS)
    assert now_ns < tick <= now_ns + PERIOD
    assert (tick - 7 * MS) % PERIOD == 0


def test_changing_delay_moves_tick_within_period():
    now_ns = 5 * PERIOD + 10 * MS
    assert next_tick(now_ns, PERIOD, 20 * MS) == 5 * PERIOD + 20 * MS
    assert next_tick(now_ns, PERIOD, 5 * MS) == 6 * PERIOD + 5 * MS


@pytest.mark.parametrize("delay_ns", [-1, PERIOD, PERIOD + 1])
def test_next_tick_requires_normalized_delay(delay_ns):
    with pytest.raises(ValueError):
        next_tick(0, PERIOD, delay_ns)


@pytest.mark.parametrize(
    "delay_ns,expected",
    [
        (0, 0),
        (30 * MS, 30 * MS),
        (PERIOD - 1, PERIOD - 1),
        # delay equal to the period is the same as no delay
        (PERIOD, 0),
        (PERIOD + DELAY_TOLERANCE_NS, DELAY_TOLERANCE_NS),
    ],
)
def test_normalize_delay(delay_ns, expected):
    assert normalize_delay(delay_ns, PERIOD) == expected


def test_normalize_delay_from_float32_seconds():
    # 0.1 s as float32 is 0.10000000149..., which rounds to 100_000_001 ns
    delay_ns = round(float(np.float32(0.1)) * 1e9)
    assert delay_ns > PERIOD
    assert normalize_delay(delay_ns, PERIOD) == delay_ns - PERIOD


@pytest.mark.parametrize("delay_ns", [-1, PERIOD + DELAY_TOLERANCE_NS + 1, 2 * PERIOD])
def test_normalize_delay_out_of_range(delay_ns):
    with pytest.raises(ValueError):
        normalize_delay(delay_ns, PERIOD)


@pytest.mark.parametrize(
    "delay_ns,new_period_ns,expected",
    [
        (30 * MS, 50 * MS, 30 * MS),
        # 10 Hz -> 20 Hz with delay above the new period
        (70 * MS, 50 * MS, 20 * MS),
        (50 * MS, 50 * MS, 0),
        (30 * MS, 200 * MS, 30 * MS),
    ],
)
def test_rebase_delay_on_period_change(delay_ns, new_period_ns, expected):
    assert rebase_delay(delay_ns, new_period_ns) == expected


def test_rebase_negative_delay():
    with pytest.raises(ValueError):
        rebase_delay(-1, PERIOD)


@pytest.mark.parametrize("period_ns", [0, -PERIOD])
def test_invalid_period(period_ns):
    with pytest.raises(ValueError):
        normalize_delay(0, period_ns)
    with pytest.raises(ValueError):
        rebase_delay(0, period_ns)
    with pytest.raises(ValueError):
        next_tick(0, period_ns, 0)


class FakeClock:

    def __init__(self, now_ns, step_ns=1000):
        self.now_ns = now_ns
        self.step_ns = step_ns
        self.sleeps = []

    def time_ns(self):
        self.now_ns += self.step_ns
        return self.now_ns

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now_ns += round(seconds * 1e9)


def test_sleep_until_sleeps_then_spins():
    clock = FakeClock(now_ns=0)
    sleep_until(50 * MS, clock=clock.time_ns, sleep=clock.sleep, spin_margin_ns=2 * MS)
    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == pytest.approx(0.048, abs=1e-5)
    assert clock.now_ns >= 50 * MS


def test_sleep_until_only_spins_near_target():
    clock = FakeClock(now_ns=0)
    sleep_until(1 * MS, clock=clock.time_ns, sleep=clock.sleep, spin_margin_ns=2 * MS)
    assert clock.sleeps == []
    assert clock.now_ns >= 1 * MS


def test_sleep_until_past_target_returns():
    clock = FakeClock(now_ns=10 * MS)
    sleep_until(1 * MS, clock=clock.time_ns, sleep=clock.sleep)
    assert clock.sleeps == []
