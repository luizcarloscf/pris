import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from opentelemetry.instrumentation.pris_wire.otlp import install
from opentelemetry.test.globals_test import reset_metrics_globals, reset_trace_globals
from opentelemetry.test.test_base import TestBase
from pris_msgs.utils.io import load
from pris_wire.core import Channel

sys.path.insert(0, str(Path(__file__).parent))
import fake_pyspin  # noqa: E402

sys.modules["PySpin"] = fake_pyspin  # type: ignore[assignment]

from pris_camera_gateway.camera import SpinnakerCamera  # noqa: E402
from pris_camera_gateway.conf.options_pb2 import CameraGatewayOptions  # noqa: E402

URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")
DEFAULT_OPTIONS = Path(__file__).parents[1] / "etc" / "conf" / "options.json"


def camera_options(**fields):
    options = load(str(DEFAULT_OPTIONS), CameraGatewayOptions).camera
    options.use_turbojpeg = False
    for name, value in fields.items():
        setattr(options, name, value)
    return options


@pytest.fixture
def make_camera():
    """A SpinnakerCamera connected to a fake camera, which is returned with it."""
    def make(fake=None, **fields):
        fake = fake or fake_pyspin.FakeCamera()
        camera = SpinnakerCamera(camera_options(**fields))
        camera.system = MagicMock()
        camera.system.GetCameras.return_value = fake_pyspin.FakeCameraList([fake])
        camera.processor = MagicMock()
        camera.processor.Convert.side_effect = lambda image, pixel_format: image
        camera.connect()
        return camera, fake
    return make


@pytest.fixture
def connect():
    channels = []

    def _connect():
        channel = Channel(URI)
        channels.append(channel)
        return channel

    yield _connect
    for channel in channels:
        channel.close()


@pytest.fixture
def channel(connect):
    return connect()


@pytest.fixture
def prefix():
    return "Test.{}".format(uuid.uuid4().hex[:8])


@pytest.fixture
def spans():
    reset_trace_globals()
    reset_metrics_globals()
    tracer_provider, exporter = TestBase.create_tracer_provider()
    meter_provider, _ = TestBase.create_meter_provider()
    shutdown = install(tracer_provider, meter_provider)
    yield exporter
    shutdown()
    reset_trace_globals()
    reset_metrics_globals()
