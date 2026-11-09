import os

import pytest
from opentelemetry.instrumentation.pris_wire.otlp import install
from opentelemetry.test.globals_test import reset_metrics_globals, reset_trace_globals
from opentelemetry.test.test_base import TestBase
from pris_wire.core import Channel

URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")


@pytest.fixture
def channel():
    channel = Channel(URI)
    yield channel
    channel.close()


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
