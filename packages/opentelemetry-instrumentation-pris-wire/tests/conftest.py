import os
import uuid

import pytest
from pris_wire.core import Channel, Subscription
from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor
from opentelemetry.test.test_base import TestBase


URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")


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
def topic(channel):
    name = "Test.{}".format(uuid.uuid4().hex[:8])
    Subscription(channel).subscribe(name)
    return name


class Telemetry:

    def __init__(self):
        self.tracer_provider, self.span_exporter = TestBase.create_tracer_provider()
        self.meter_provider, self.metric_reader = TestBase.create_meter_provider()

    def spans(self):
        return self.span_exporter.get_finished_spans()

    def metrics(self):
        found = {}
        data = self.metric_reader.get_metrics_data()
        for resource_metrics in (data.resource_metrics if data else []):
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    found.setdefault(metric.name, []).extend(metric.data.data_points)
        return found


@pytest.fixture
def telemetry():
    return Telemetry()


@pytest.fixture
def instrument(telemetry):
    instrumentor = PrisWireInstrumentor()

    def _instrument(**kwargs):
        instrumentor.instrument(
            tracer_provider=telemetry.tracer_provider,
            meter_provider=telemetry.meter_provider,
            **kwargs,
        )

    yield _instrument
    if instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.uninstrument()
