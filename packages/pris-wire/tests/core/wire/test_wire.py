from importlib import resources

import amqp

from pris_wire.core import ContentType, Message, Status, StatusCode, now
from pris_wire.core.wire import wire_pb2
from pris_wire.core.wire.conversion import WireV1


def test_amqp_round_trip():
    sent = Message(content=b'{"field":"value"}', content_type=ContentType.JSON)
    sent.created_at = int(now() * 1000) / 1000.0
    sent.reply_to = "reply_to"
    sent.subscription_id = "subscription_id"
    sent.topic = "MyTopic"
    sent.timeout = 2.5
    sent.status = Status(code=StatusCode.FAILED_PRECONDITION, why="Bad Args...")
    sent.metadata = {"key": "value"}

    amqp_message = amqp.Message(channel=None, body=sent.body, **WireV1.to_amqp_properties(sent))
    amqp_message.delivery_info = {
        "routing_key": sent.topic,
        "consumer_tag": sent.subscription_id,
    }
    received = WireV1.from_amqp_message(amqp_message)

    assert str(received) == str(sent)
    assert received.correlation_id == sent.correlation_id


def test_proto_is_packaged():
    assert resources.files("pris_wire.core.wire").joinpath("wire.proto").is_file()
    assert wire_pb2.DESCRIPTOR.name == "wire.proto"
