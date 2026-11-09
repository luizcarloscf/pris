import os
import uuid

import pytest
from opentelemetry.instrumentation.pris_wire.otlp import install
from opentelemetry.test.globals_test import reset_metrics_globals, reset_trace_globals
from opentelemetry.test.test_base import TestBase
from pris_wire.core import Channel

URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")
MANAGEMENT_URI = os.getenv("RABBITMQ_MANAGEMENT_URI", "http://guest:guest@localhost:15672")


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
def management_uri():
    return MANAGEMENT_URI


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
