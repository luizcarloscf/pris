import collections
import socket

import amqp
import pytest
from pris_wire.core import Message
from pris_wire.core.channel import Channel


class FakeAmqpChannel:
    def __init__(self, connection):
        self.connection = connection

    def basic_publish(self, message, exchange, routing_key, immediate, mandatory):
        while self.connection.pending:
            self.connection.drain_events(timeout=0)


class FakeConnection:

    def __init__(self, channel):
        self.channel = channel
        self.pending = []
        self.timeouts = []

    def deliver(self, body, routing_key="Topic"):
        message = amqp.Message(body=body)
        message.delivery_info = {"routing_key": routing_key, "consumer_tag": "consumer"}
        self.pending.append(message)

    def drain_events(self, timeout=None):
        self.timeouts.append(timeout)
        if not self.pending:
            raise socket.timeout()
        self.channel._on_message(self.pending.pop(0))


@pytest.fixture
def channel():
    channel = Channel.__new__(Channel)
    channel._exchange = "pris"
    channel.connection = FakeConnection(channel)
    channel._channel = FakeAmqpChannel(channel.connection)
    channel.subscriptions = []
    channel._deliveries = collections.deque()
    return channel


def test_delivery_during_publish_is_consumed(channel):
    channel.connection.deliver(b"request")
    channel.publish(Message(content=b"reply"), topic="Other")

    assert channel.consume(timeout=0).body == b"request"


def test_deliveries_during_publish_keep_their_order(channel):
    channel.connection.deliver(b"first")
    channel.connection.deliver(b"second")
    channel.publish(Message(content=b"reply"), topic="Other")
    channel.connection.deliver(b"third")

    assert [channel.consume(timeout=0).body for _ in range(3)] == [
        b"first", b"second", b"third"]


def test_consume_times_out_when_nothing_is_queued(channel):
    channel.connection.deliver(b"request")
    channel.publish(Message(content=b"reply"), topic="Other")
    channel.consume(timeout=0)

    with pytest.raises(socket.timeout):
        channel.consume(timeout=0)


def test_consume_for_returns_message(channel):
    channel.connection.deliver(b"request")

    assert channel.consume_for(1.0).body == b"request"
    assert channel.connection.timeouts == [1.0]


def test_consume_for_returns_none_on_timeout(channel):
    assert channel.consume_for(1.0) is None


def test_consume_for_negative_timeout_does_not_block(channel):
    assert channel.consume_for(-1.0) is None
    assert channel.connection.timeouts == [0.0]


def test_consume_until_waits_for_the_time_left(channel, monkeypatch):
    monkeypatch.setattr("pris_wire.core.channel.time.time", lambda: 100.0)
    channel.connection.deliver(b"request")

    assert channel.consume_until(102.5).body == b"request"
    assert channel.consume_until(102.5) is None
    assert channel.connection.timeouts == [2.5, 2.5]


def test_consume_until_past_deadline_does_not_block(channel, monkeypatch):
    monkeypatch.setattr("pris_wire.core.channel.time.time", lambda: 100.0)

    assert channel.consume_until(99.0) is None
    assert channel.connection.timeouts == [0.0]


def test_consume_ready_returns_everything_ready(channel):
    channel.connection.deliver(b"first")
    channel.publish(Message(content=b"reply"), topic="Other")
    channel.connection.deliver(b"second")

    assert [message.body for message in channel.consume_ready()] == [b"first", b"second"]
    assert set(channel.connection.timeouts) == {0.0}


def test_consume_ready_without_messages(channel):
    assert channel.consume_ready() == []
