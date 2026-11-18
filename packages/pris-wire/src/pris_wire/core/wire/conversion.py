from __future__ import annotations

from typing import Any

import amqp
from google.protobuf import json_format

from ..message import Message
from . import wire_pb2
from .content_type import content_type_from_wire, content_type_to_wire
from .status import Status, StatusCode


class WireV1:
    """The mapping between a Message and an AMQP message."""

    @staticmethod
    def from_amqp_message(amqp_message: amqp.Message) -> Message:
        """Convert a received AMQP message.

        Args:
            amqp_message: a message delivered by the broker.

        Returns:
            A new message with the body and properties of `amqp_message`.

        Raises:
            RuntimeError: the content_type property is unknown.
        """
        body = amqp_message.body
        message = Message(body if isinstance(body, bytes) else body.encode("latin"))

        delivery_info = amqp_message.delivery_info
        message.topic = delivery_info["routing_key"]
        message.subscription_id = delivery_info["consumer_tag"]
        if delivery_info.get("delivery_tag") is not None:
            message.delivery_tag = delivery_info["delivery_tag"]

        properties = amqp_message.properties
        if "content_type" in properties:
            message.content_type = content_type_from_wire(properties["content_type"])
        if "correlation_id" in properties:
            message.correlation_id = int(properties["correlation_id"], 16)
        if "reply_to" in properties:
            message.reply_to = properties["reply_to"]
        if "expiration" in properties:
            message.timeout = int(properties["expiration"]) / 1000.0
        if "timestamp" in properties:
            message.created_at = properties["timestamp"] / 1000.0

        if "application_headers" in properties:
            headers = dict(properties["application_headers"])
            if "rpc-status" in headers:
                status = json_format.Parse(headers.pop("rpc-status"), wire_pb2.Status())
                message.status = Status(code=StatusCode(status.code), why=status.why)
            message.metadata = headers

        return message

    @staticmethod
    def to_amqp_properties(message: Message) -> dict[str, Any]:
        """Convert a message's properties for publishing.

        Args:
            message: the message to publish.

        Returns:
            The keyword arguments of amqp.Message: timestamp, content_type, correlation_id,
            reply_to, expiration and application_headers (metadata and rpc-status).
        """
        headers = dict(message.metadata)
        if message.status is not None:
            status = wire_pb2.Status(code=message.status.code.value, why=message.status.why)
            headers["rpc-status"] = json_format.MessageToJson(
                status, indent=0, always_print_fields_with_no_presence=True
            )

        properties: dict[str, Any] = {
            "timestamp": int(message.created_at * 1000),
            "application_headers": headers,
        }
        if message.content_type is not None:
            properties["content_type"] = content_type_to_wire(message.content_type)
        if message.correlation_id is not None:
            properties["correlation_id"] = "{:X}".format(message.correlation_id)
        if message.has_reply_to():
            properties["reply_to"] = message.reply_to
        if message.timeout is not None:
            properties["expiration"] = str(int(message.timeout * 1000))

        return properties
