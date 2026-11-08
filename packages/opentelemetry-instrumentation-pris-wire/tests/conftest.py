import collections
import socket
from types import SimpleNamespace

import pytest
from pris_wire.core.channel import Channel
from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor
from opentelemetry.test.test_base import TestBase


class FakeAmqpChannel:
    def __init__(self):
        self.published = []
        self.error = None
        self.bindings = {}
        self.consumers = {}

    def queue_declare(self, queue, **kwargs):
        pass

    def queue_bind(self, queue, exchange, routing_key):
        self.bindings[routing_key] = queue

    def queue_unbind(self, queue, exchange, routing_key):
        self.bindings.pop(routing_key, None)

    def basic_consume(self, queue, callback, consumer_tag, **kwargs):
        self.consumers[queue] = consumer_tag

    def basic_publish(self, message, exchange, routing_key, immediate, mandatory):
        if self.error is not None:
            raise self.error
        self.published.append(SimpleNamespace(
            message=message, exchange=exchange, routing_key=routing_key))


class FakeConnection:
    host = "broker.local:5672"

    def __init__(self, channel):
        self.channel = channel
        self.queue = []
        self.error = None

    def drain_events(self, timeout=None):
        if self.error is not None:
            raise self.error
        if not self.queue:
            raise socket.timeout()
        self.channel._on_message(self.queue.pop(0))

    def loopback(self):
        amqp_channel = self.channel._channel
        for sent in amqp_channel.published:
            queue = amqp_channel.bindings.get(sent.routing_key)
            sent.message.delivery_info = {
                "routing_key": sent.routing_key,
                "consumer_tag": amqp_channel.consumers.get(queue, "consumer"),
            }
            self.queue.append(sent.message)
        self.channel._channel.published.clear()


@pytest.fixture
def channel():
    channel = Channel.__new__(Channel)
    channel._exchange = "pris"
    channel._channel = FakeAmqpChannel()
    channel.connection = FakeConnection(channel)
    channel.subscriptions = []
    channel._deliveries = collections.deque()
    return channel


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
