import time

import pytest
from google.protobuf.struct_pb2 import Struct

from pris_wire.core import ContentType, Message, Status


def test_default_constructor():
    message = Message()
    assert not message.has_body()
    assert not message.has_topic()
    assert message.has_created_at()
    assert not message.has_content_type()
    assert not message.has_correlation_id()
    assert not message.has_reply_to()
    assert not message.has_subscription_id()
    assert not message.has_timeout()
    assert not message.has_metadata()


def test_created_at_is_unix_time():
    before = time.time()
    message = Message()
    assert before <= message.created_at <= time.time()


@pytest.mark.parametrize("property, valid, invalid", [
    ("topic", "str", -1),
    ("reply_to", "str", -1),
    ("body", b"bytes", -1),
    ("subscription_id", "str", -1),
    ("correlation_id", -1, "str"),
    ("content_type", ContentType.PROTOBUF, "str"),
    ("timeout", 1.5, "str"),
    ("status", Status(), "str"),
    ("metadata", {}, "str"),
])
def test_setters_check_types(property, valid, invalid):
    message = Message()
    setattr(message, property, valid)
    assert getattr(message, property) == valid
    with pytest.raises(TypeError):
        setattr(message, property, invalid)


@pytest.mark.parametrize("attr, value, checker", [
    ("topic", "string", Message.has_topic),
    ("reply_to", "string", Message.has_reply_to),
    ("subscription_id", "string", Message.has_subscription_id),
    ("correlation_id", -1, Message.has_correlation_id),
    ("body", b"string", Message.has_body),
    ("content_type", ContentType.JSON, Message.has_content_type),
    ("timeout", 10.0, Message.has_timeout),
    ("status", Status(), Message.has_status),
])
def test_has_field(attr, value, checker):
    message = Message()
    assert not checker(message)
    setattr(message, attr, value)
    assert checker(message)


@pytest.mark.parametrize("content_type", [ContentType.PROTOBUF, ContentType.JSON])
def test_pack_unpack_protobuf(content_type):
    struct = Struct()
    struct.fields["number"].number_value = 0.1212121921839893
    struct.fields["string"].string_value = "text"
    message = Message(content_type=content_type)
    message.pack(struct)
    assert message.unpack(Struct) == struct


def test_dict_is_packed_as_json_by_default():
    dictionary = {"key": 0.1233444444, "text": "hold the door", "default": 0}
    message = Message(content=dictionary)
    assert message.content_type == ContentType.JSON
    assert message.unpack() == dictionary


def test_dict_with_protobuf_content_type():
    dictionary = {"key": 0.5, "text": "value"}
    message = Message(content_type=ContentType.PROTOBUF)
    message.pack(dictionary)
    assert message.unpack() == dictionary


def test_create_reply():
    request = Message(reply_to="reply_to", content_type=ContentType.JSON)
    request.topic = "topic"
    reply = request.create_reply()
    assert reply.topic == "reply_to"
    assert reply.correlation_id == request.correlation_id
    assert reply.content_type == ContentType.JSON


def test_create_reply_empty_request():
    request = Message()
    request.topic = "topic"
    reply = request.create_reply()
    assert reply.topic is None
    assert reply.correlation_id is None
    assert reply.content_type is None


def test_constructor():
    message = Message(content=b"body", reply_to="reply_to", content_type=ContentType.JSON)
    assert message.body == b"body"
    assert message.reply_to == "reply_to"
    assert message.content_type == ContentType.JSON
