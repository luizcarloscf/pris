import os
import uuid

import cv2
import numpy as np
import pytest
from opentelemetry.instrumentation.pris_wire.otlp import install
from opentelemetry.test.globals_test import reset_metrics_globals, reset_trace_globals
from opentelemetry.test.test_base import TestBase
from pris_msgs.image_pb2 import Image
from pris_wire.core import Channel

URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")


def render(markers, size=(480, 640), dictionary=cv2.aruco.DICT_4X4_50, marker_size=120):
    canvas = np.full(size, 255, dtype=np.uint8)
    aruco_dictionary = cv2.aruco.getPredefinedDictionary(dictionary)
    for id, x, y in markers:
        canvas[y:y + marker_size, x:x + marker_size] = cv2.aruco.generateImageMarker(
            aruco_dictionary, id, marker_size)
    return canvas


@pytest.fixture
def scene():
    def make(markers, extension=".png", **kwargs):
        ok, data = cv2.imencode(extension, render(markers, **kwargs))
        assert ok
        return Image(data=data.tobytes())
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
def topic():
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
