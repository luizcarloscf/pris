import pytest

from pris_camera_gateway.clock import ClockMapper, LatchSample

MS = 1_000_000
HOST_EPOCH_NS = 1_761_000_000_000_000_000


def make_sample(camera_ns, offset_ns, round_trip_ns, ns_per_tick=1.0, latch_at=0.5):
    """Sample where the latch happened `latch_at` of the way through the round trip."""
    host_ns = camera_ns + offset_ns
    before = host_ns - round(round_trip_ns * latch_at)
    return LatchSample(
        host_before_ns=before,
        camera_ticks=round(camera_ns / ns_per_tick),
        host_after_ns=before + round_trip_ns,
    )


def test_not_ready_before_update():
    mapper = ClockMapper(ns_per_tick=1.0)
    assert not mapper.ready
    with pytest.raises(RuntimeError):
        mapper.to_host_ns(0)


@pytest.mark.parametrize("ns_per_tick", [0, -1.0])
def test_invalid_ns_per_tick(ns_per_tick):
    with pytest.raises(ValueError):
        ClockMapper(ns_per_tick=ns_per_tick)


def test_empty_samples():
    with pytest.raises(ValueError):
        ClockMapper(ns_per_tick=1.0).update([])


def test_constant_offset():
    mapper = ClockMapper(ns_per_tick=1.0)
    mapper.update([
        make_sample(camera_ns=5_000 * MS, offset_ns=HOST_EPOCH_NS, round_trip_ns=200_000),
    ])
    assert mapper.to_host_ns(5_000 * MS) == 5_000 * MS + HOST_EPOCH_NS
    assert mapper.to_host_ns(5_100 * MS) == 5_100 * MS + HOST_EPOCH_NS


def test_picks_sample_with_smallest_round_trip():
    mapper = ClockMapper(ns_per_tick=1.0)
    camera_ns = 1_000 * MS
    samples = [
        # slow round trips, latched far from the middle: large error
        make_sample(camera_ns, HOST_EPOCH_NS, round_trip_ns=5 * MS, latch_at=0.9),
        make_sample(camera_ns, HOST_EPOCH_NS, round_trip_ns=50_000, latch_at=0.5),
        make_sample(camera_ns, HOST_EPOCH_NS, round_trip_ns=3 * MS, latch_at=0.1),
    ]
    mapper.update(samples)
    assert abs(mapper.to_host_ns(camera_ns) - (camera_ns + HOST_EPOCH_NS)) <= 1


def test_tick_frequency_conversion():
    # GigE cameras may report ticks at a frequency, e.g. 125 MHz = 8 ns/tick
    ns_per_tick = 8.0
    mapper = ClockMapper(ns_per_tick=ns_per_tick)
    camera_ns = 2_000 * MS
    mapper.update([
        make_sample(camera_ns, HOST_EPOCH_NS, round_trip_ns=100_000, ns_per_tick=ns_per_tick),
    ])
    later_ticks = round((camera_ns + 40 * MS) / ns_per_tick)
    assert mapper.to_host_ns(later_ticks) == camera_ns + 40 * MS + HOST_EPOCH_NS


def test_drift_is_compensated():
    drift_ppm = 50.0
    slope = 1 + drift_ppm * 1e-6
    mapper = ClockMapper(ns_per_tick=1.0, window=10)
    # one latch burst per second, during 10 seconds
    for second in range(10):
        camera_ns = second * 1_000 * MS
        host_ns = HOST_EPOCH_NS + round(camera_ns * slope)
        mapper.update([LatchSample(host_ns - 50_000, camera_ns, host_ns + 50_000)])
    assert mapper.drift_ppm == pytest.approx(drift_ppm, rel=1e-3)
    # half a second after the last latch, the extrapolation stays below 1 us
    camera_ns = 9_500 * MS
    expected = HOST_EPOCH_NS + round(camera_ns * slope)
    assert abs(mapper.to_host_ns(camera_ns) - expected) < 1_000


def test_without_drift_compensation_error_grows():
    # sanity check of the scenario above: a pure offset would be ~25 us off
    slope = 1 + 50e-6
    mapper = ClockMapper(ns_per_tick=1.0, window=1)
    for second in range(10):
        camera_ns = second * 1_000 * MS
        host_ns = HOST_EPOCH_NS + round(camera_ns * slope)
        mapper.update([LatchSample(host_ns - 50_000, camera_ns, host_ns + 50_000)])
    camera_ns = 9_500 * MS
    expected = HOST_EPOCH_NS + round(camera_ns * slope)
    assert abs(mapper.to_host_ns(camera_ns) - expected) > 20_000


def test_camera_counter_reset_discards_old_points():
    mapper = ClockMapper(ns_per_tick=1.0, window=10)
    mapper.update([make_sample(9_000 * MS, HOST_EPOCH_NS, round_trip_ns=100_000)])
    mapper.update([make_sample(10_000 * MS, HOST_EPOCH_NS, round_trip_ns=100_000)])
    # the counter restarted from zero with a new offset
    new_offset = HOST_EPOCH_NS + 10_500 * MS
    mapper.update([make_sample(1 * MS, new_offset, round_trip_ns=100_000)])
    assert mapper.drift_ppm == 0.0
    assert mapper.to_host_ns(2 * MS) == 2 * MS + new_offset
