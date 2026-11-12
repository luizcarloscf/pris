import time
from unittest.mock import MagicMock

import cv2
import fake_pyspin
import numpy as np
import pytest
from google.protobuf.wrappers_pb2 import FloatValue
from pris_msgs.image_pb2 import ColorSpace, ColorSpaces, ImageFormats
from pris_wire.core import StatusCode

from pris_camera_gateway.conf.options_pb2 import TriggerMode
from pris_camera_gateway.nodes import StatusException

SCHEDULED = TriggerMode.SOFTWARE_SCHEDULED
NS_PER_TICK = 8


def trigger_writes(node_map):
    return [write for write in node_map.writes if write[0].startswith("Trigger")]


def ticking_camera():
    """A camera whose counter runs at 1/NS_PER_TICK of the host clock, 1 s ahead, and whose
    images were exposed 50 ms before they are read."""
    fake = fake_pyspin.FakeCamera()
    node_map = fake.node_map

    def camera_ns(host_ns):
        return host_ns + 1_000_000_000

    node_map.GetNode("GevTimestampTickFrequency").value = 1_000_000_000 // NS_PER_TICK
    node_map.on_execute["TimestampLatch"] = lambda: setattr(
        node_map.GetNode("TimestampLatchValue"), "value", camera_ns(time.time_ns()) // NS_PER_TICK)
    fake.image_timestamp_ns = lambda: camera_ns(time.time_ns() - 50_000_000)
    return fake


def test_connect_scheduled_enables_the_software_trigger(make_camera):
    _, fake = make_camera(trigger_mode=SCHEDULED)

    assert trigger_writes(fake.node_map) == [
        ("TriggerMode", "Off"),
        ("TriggerSelector", "FrameStart"),
        ("TriggerSource", "Software"),
        ("TriggerMode", "On"),
    ]
    assert fake.stream_node_map.value("StreamBufferHandlingMode") == "NewestOnly"


def test_connect_free_run_keeps_the_trigger_off(make_camera):
    _, fake = make_camera()

    assert trigger_writes(fake.node_map) == [("TriggerMode", "Off")]
    assert fake.node_map.value("GevSCPSPacketSize") == 1400
    assert fake.stream_node_map.value("StreamPacketResendMaxRequests") == 5


def test_connect_without_a_camera_at_the_ip(make_camera):
    with pytest.raises(RuntimeError, match="no camera at 10.20.6.9"):
        make_camera(ip="10.20.6.9")


def test_free_run_rejects_a_delay_and_sets_the_camera_frame_rate(make_camera):
    camera, fake = make_camera()

    with pytest.raises(StatusException) as ex:
        camera.set_delay(FloatValue(value=0.01))
    assert ex.value.status.code == StatusCode.FAILED_PRECONDITION
    camera.set_sampling_rate(FloatValue(value=20.0))
    assert fake.node_map.value("AcquisitionFrameRate") == 20.0
    assert fake.node_map.value("AcquisitionFrameRateEnabled") is True


def test_blackfly_s_frame_rate_node(make_camera):
    camera, fake = make_camera(fake_pyspin.FakeCamera(model="Blackfly S BFS-PGE-16S2C"))

    camera.set_sampling_rate(FloatValue(value=20.0))

    assert fake.node_map.value("AcquisitionFrameRateEnable") is True
    assert "AcquisitionFrameRateEnabled" not in fake.node_map.nodes


def test_scheduled_sampling_rate_and_delay(make_camera):
    camera, fake = make_camera(trigger_mode=SCHEDULED)

    camera.set_sampling_rate(FloatValue(value=50.0))
    camera.set_delay(FloatValue(value=0.015))
    assert camera.get_sampling_rate().value == pytest.approx(50.0)
    assert camera.get_delay().value == pytest.approx(0.015)
    assert "AcquisitionFrameRate" not in fake.node_map.nodes
    camera.set_sampling_rate(FloatValue(value=100.0))
    assert camera.get_delay().value == pytest.approx(0.005)
    with pytest.raises(StatusException) as ex:
        camera.set_delay(FloatValue(value=0.5))
    assert ex.value.status.code == StatusCode.INVALID_ARGUMENT


def test_frames_are_stamped_with_the_camera_clock(make_camera):
    camera, fake = make_camera(ticking_camera())
    assert camera.mapper is not None

    before = time.time_ns()
    capture = camera.grab(100)

    assert before - 52_000_000 < capture.timestamp_ns < before - 48_000_000
    assert fake.images[-1].released
    decoded = cv2.imdecode(np.frombuffer(capture.image.data, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape == (8, 8, 3)


@pytest.mark.parametrize("missing", ["GevTimestampTickFrequency", "TimestampLatch"])
def test_frames_are_stamped_on_arrival_without_a_latch(make_camera, missing):
    fake = ticking_camera()
    fake.node_map.missing.add(missing)
    camera, _ = make_camera(fake)
    assert camera.mapper is None

    before = time.time_ns()
    assert before <= camera.grab(100).timestamp_ns <= time.time_ns()


def test_incomplete_images_and_timeouts_give_nothing(make_camera):
    camera, fake = make_camera()

    fake.incomplete = True
    assert camera.grab(100) is None
    assert fake.images[-1].released
    fake.timeout = True
    assert camera.grab(100) is None


def test_sync_clock_latches_a_burst(make_camera):
    camera, fake = make_camera(ticking_camera(), latch_samples=4)
    latch = fake.node_map.GetNode("TimestampLatch")
    before = latch.executed

    camera.sync_clock()

    assert latch.executed == before + 4


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WebP"])
def test_formats_are_encoded_with_opencv(make_camera, image_format):
    camera, _ = make_camera()
    camera.image_format = ImageFormats.Value(image_format)

    data = camera.grab(100).image.data

    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert decoded.shape[:2] == (8, 8)


def test_turbojpeg_encodes_jpeg(make_camera, monkeypatch):
    from pris_msgs.utils import image as image_module
    encoder = MagicMock()
    encoder.encode.return_value = b"turbo"
    monkeypatch.setattr(image_module, "_turbojpeg", lambda: encoder)
    camera, _ = make_camera(use_turbojpeg=True)

    assert camera.grab(100).image.data == b"turbo"


def test_an_image_that_cant_be_encoded_gives_nothing(make_camera):
    camera, _ = make_camera()
    camera.compression = 2.0

    assert camera.grab(100) is None


def test_color_space_and_region_only_change_while_stopped(make_camera):
    camera, fake = make_camera()
    camera.set_color_space(ColorSpace(value=ColorSpaces.GRAY))
    assert fake.node_map.value("PixelFormat") == "Mono8"

    camera.start()
    with pytest.raises(StatusException) as ex:
        camera.set_color_space(ColorSpace(value=ColorSpaces.RGB))
    assert ex.value.status.code == StatusCode.FAILED_PRECONDITION
    with pytest.raises(StatusException):
        camera.set_region(camera.get_region())
