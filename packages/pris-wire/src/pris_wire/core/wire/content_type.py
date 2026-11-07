from __future__ import annotations

from enum import Enum

from ..utils import assert_type
from . import wire_pb2


class ContentType(Enum):
    """How a message's body is serialized."""

    PROTOBUF = wire_pb2.ContentType.Value("PROTOBUF")
    JSON = wire_pb2.ContentType.Value("JSON")


def content_type_to_wire(content_type: ContentType) -> str:
    """Return the AMQP content_type property of a ContentType.

    Args:
        content_type: the content type.

    Returns:
        "application/x-protobuf" or "application/json".

    Raises:
        TypeError: `content_type` isn't a ContentType.
    """
    assert_type(content_type, ContentType, "content_type")
    if content_type == ContentType.PROTOBUF:
        return 'application/x-protobuf'

    if content_type == ContentType.JSON:
        return 'application/json'

    raise NotImplementedError(
        "ContentType '{}' wire serialization not implemented".format(
            content_type.name))


def content_type_from_wire(string: str) -> ContentType:
    """Return the ContentType of an AMQP content_type property.

    Args:
        string: "application/x-protobuf" or "application/json".

    Returns:
        The content type.

    Raises:
        TypeError: `string` isn't a str.
        RuntimeError: `string` is another content type.
    """
    assert_type(string, str, "string")
    if string == 'application/x-protobuf':
        return ContentType.PROTOBUF

    if string == 'application/json':
        return ContentType.JSON

    raise RuntimeError("Bad content_type {}".format(string))
