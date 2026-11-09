import os
import threading
import uuid

import pytest
from pris_wire.core import Channel
from pris_wire.rpc import ServiceProvider

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
def topic():
    return "Test.{}".format(uuid.uuid4().hex[:8])


@pytest.fixture
def serve(connect):
    threads = []

    def _serve(topic, function, request_type, reply_type):
        channel = connect()
        provider = ServiceProvider(channel)
        provider.delegate(topic, function, request_type, reply_type)
        thread = threading.Thread(target=lambda: provider.serve(channel.consume(timeout=2.0)),
                                  daemon=True)
        thread.start()
        threads.append(thread)

    yield _serve
    for thread in threads:
        thread.join(timeout=3.0)
