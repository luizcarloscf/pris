import socket
import time

import pytest
from google.protobuf.struct_pb2 import Struct
from pris_wire.core import Message, Status, StatusCode, Subscription

from pris_common.rpc import call


def echo(request, context):
    if "fail" in request.fields:
        return Status(StatusCode.FAILED_PRECONDITION, "asked to fail")
    return request


@pytest.fixture
def server(serve, topic):
    serve(topic, echo, Struct, Struct)


def test_the_reply(channel, topic, server):
    request = Struct()
    request.update({"value": 42})

    reply = call(channel, request, topic)

    assert reply.unpack(Struct) == request


def test_an_error_status_raises(channel, topic, server):
    request = Struct()
    request.update({"fail": True})

    with pytest.raises(RuntimeError, match="FAILED_PRECONDITION"):
        call(channel, request, topic)


def test_no_reply_times_out(channel, topic):
    start = time.time()

    with pytest.raises(socket.timeout):
        call(channel, Struct(), topic, timeout=0.3)

    assert time.time() - start >= 0.3


def test_other_messages_are_dropped(channel, topic, server):
    other = Subscription(channel)
    channel.publish(Message(content=b"not a reply"), topic=other.name)

    assert call(channel, Struct(), topic).unpack(Struct) == Struct()
