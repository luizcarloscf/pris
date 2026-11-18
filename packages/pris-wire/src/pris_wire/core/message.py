from __future__ import annotations

from datetime import datetime
from typing import Any

from google.protobuf import json_format as pb
from google.protobuf.message import Message as ProtoMessage
from google.protobuf.struct_pb2 import Struct

from .subscription import Subscription
from .utils import assert_type, new_uuid, now
from .wire.content_type import ContentType
from .wire.status import Status


class Message:
    """A message on the bus: a body and its properties (topic, reply_to, status, ...)."""

    def __init__(
        self,
        content: bytes | ProtoMessage | dict[str, Any] | None = None,
        reply_to: str | Subscription | None = None,
        content_type: ContentType | None = None,
    ) -> None:
        """Create a message, created_at now.

        Args:
            content: the body as bytes, or a protobuf message or dict to pack with
                `content_type`.
            reply_to: where the reply should go; see the reply_to property.
            content_type: how `content` is serialized; by default PROTOBUF for a protobuf message
                and JSON for a dict.

        Raises:
            TypeError: `reply_to` or `content_type` has the wrong type.
        """
        self._topic: str | None = None
        self._body = b""
        self._reply_to: str | None = None
        self._subscription_id: str | None = None
        self._delivery_tag: int | None = None
        self._correlation_id: int | None = None
        self._content_type: ContentType | None = None
        self._created_at = now()
        self._metadata: dict[str, Any] = {}
        self._timeout: float | None = None
        self._status: Status | None = None

        if reply_to is not None:
            self.reply_to = reply_to

        if content_type is not None:
            self.content_type = content_type

        if content is not None:
            if isinstance(content, bytes):
                self.body = content
            else:
                self.pack(content)

    def __str__(self) -> str:
        fields = [
            "topic = '{}'".format(self.topic or ""),
            "created_at = {}".format(datetime.fromtimestamp(self.created_at)),
            "correlation_id = {}".format(self.correlation_id),
            "reply_to = '{}'".format(self.reply_to or ""),
            "subscription_id = '{}'".format(self.subscription_id or ""),
            "timeout = {}".format(self.timeout),
            "status = {}".format(self.status),
            "metadata = {}".format(self.metadata),
            "content_type = {}".format(self.content_type),
            "body[{}] = {!r}".format(len(self.body), self.body),
        ]
        return "{\n" + "".join("  {}\n".format(field) for field in fields) + "}"

    def short_string(self) -> str:
        """Return the message's properties on one line, leaving out the empty ones."""
        fields = [
            "topic='{}'".format(self.topic),
            "created_at={}".format(datetime.fromtimestamp(self.created_at)),
        ]
        if self.has_correlation_id():
            fields.append("correlation_id={}".format(self.correlation_id))
        if self.has_reply_to():
            fields.append("reply_to='{}'".format(self.reply_to))
        if self.has_subscription_id():
            fields.append("subscription_id='{}'".format(self.subscription_id))
        if self.has_timeout():
            fields.append("timeout={}".format(self.timeout))
        if self.has_status():
            fields.append("status={}".format(self.status))
        if self.has_metadata():
            fields.append("metadata={}".format(self.metadata))
        if self.has_content_type():
            fields.append("content_type={}".format(self.content_type))
        fields.append("body[{}]={!r}".format(len(self.body), self.body))
        return "{" + " ".join(fields) + "}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def create_reply(self) -> Message:
        """Return a new message addressed to this one's reply_to, with its correlation_id and
        content_type."""
        reply = Message()
        if self._reply_to:
            reply.topic = self._reply_to
        if self._correlation_id is not None:
            reply.correlation_id = self._correlation_id
        if self._content_type is not None:
            reply.content_type = self._content_type
        return reply

    @property
    def topic(self) -> str | None:
        """Where the message was or will be published; set it to a str (TypeError otherwise)."""
        return self._topic

    @topic.setter
    def topic(self, topic: str) -> None:
        assert_type(topic, str, "topic")
        self._topic = topic

    def has_topic(self) -> bool:
        """Return True if the topic is set."""
        return bool(self._topic)

    @property
    def reply_to(self) -> str | None:
        """Where the reply should be published.

        Set it to a topic, or to a Subscription to use its queue and id (TypeError otherwise);
        setting it also gives the message a correlation_id if it has none.
        """
        return self._reply_to

    @reply_to.setter
    def reply_to(self, value: str | Subscription) -> None:
        assert_type(value, (str, Subscription), "reply_to")

        if self.correlation_id is None:
            self.correlation_id = new_uuid()

        if isinstance(value, Subscription):
            self._reply_to = value.name
            self.subscription_id = value.id
        else:
            self._reply_to = value

    def has_reply_to(self) -> bool:
        """Return True if reply_to is set."""
        return bool(self._reply_to)

    @property
    def subscription_id(self) -> str | None:
        """The id of the subscription the message was received by; a str (TypeError otherwise)."""
        return self._subscription_id

    @subscription_id.setter
    def subscription_id(self, value: str) -> None:
        assert_type(value, str, "subscription_id")
        self._subscription_id = value

    def has_subscription_id(self) -> bool:
        """Return True if subscription_id is set."""
        return bool(self._subscription_id)

    @property
    def delivery_tag(self) -> int | None:
        """The broker's tag of a received message, for Channel.ack and Channel.reject; an int
        (TypeError otherwise)."""
        return self._delivery_tag

    @delivery_tag.setter
    def delivery_tag(self, value: int) -> None:
        assert_type(value, int, "delivery_tag")
        self._delivery_tag = value

    def has_delivery_tag(self) -> bool:
        """Return True if delivery_tag is set."""
        return self._delivery_tag is not None

    @property
    def correlation_id(self) -> int | None:
        """The id that matches a reply to its request; an int (TypeError otherwise)."""
        return self._correlation_id

    @correlation_id.setter
    def correlation_id(self, value: int) -> None:
        assert_type(value, int, "correlation_id")
        self._correlation_id = value

    def has_correlation_id(self) -> bool:
        """Return True if correlation_id is set."""
        return self._correlation_id is not None

    @property
    def body(self) -> bytes:
        """The raw content; bytes (TypeError otherwise)."""
        return self._body

    @body.setter
    def body(self, value: bytes) -> None:
        assert_type(value, bytes, "body")
        self._body = value

    def has_body(self) -> bool:
        """Return True if the body isn't empty."""
        return bool(self._body)

    @property
    def content_type(self) -> ContentType | None:
        """How the body is serialized; a ContentType (TypeError otherwise)."""
        return self._content_type

    @content_type.setter
    def content_type(self, value: ContentType) -> None:
        assert_type(value, ContentType, "content_type")
        self._content_type = value

    def has_content_type(self) -> bool:
        """Return True if content_type is set."""
        return self._content_type is not None

    @property
    def created_at(self) -> float:
        """When the message was created, in seconds since the epoch."""
        return self._created_at

    @created_at.setter
    def created_at(self, timestamp: float) -> None:
        self._created_at = timestamp

    @property
    def metadata(self) -> dict[str, Any]:
        """Extra key-value pairs, sent as AMQP headers; a dict (TypeError otherwise)."""
        return self._metadata

    @metadata.setter
    def metadata(self, value: dict[str, Any]) -> None:
        assert_type(value, dict, "metadata")
        self._metadata = value

    def has_metadata(self) -> bool:
        """Return True if metadata isn't empty."""
        return len(self._metadata) != 0

    @property
    def timeout(self) -> float | None:
        """Seconds after created_at when the message expires; a float or int (TypeError
        otherwise)."""
        return self._timeout

    @timeout.setter
    def timeout(self, seconds: float) -> None:
        assert_type(seconds, (float, int), "timeout")
        self._timeout = seconds

    def has_timeout(self) -> bool:
        """Return True if timeout is set."""
        return self._timeout is not None

    def deadline_exceeded(self) -> bool:
        """Return True if the message has a timeout and created_at + timeout has passed."""
        if self._timeout is None:
            return False
        return now() > self.created_at + self._timeout

    @property
    def status(self) -> Status | None:
        """The result of the request this message replies to; a Status (TypeError otherwise)."""
        return self._status

    @status.setter
    def status(self, value: Status) -> None:
        assert_type(value, Status, "status")
        self._status = value

    def has_status(self) -> bool:
        """Return True if status is set."""
        return self._status is not None

    def pack(self, obj: ProtoMessage | dict[str, Any]) -> None:
        """Serialize an object into the body, with the message's content_type.

        Without a content_type, a dict is packed as JSON and a protobuf message as PROTOBUF, and
        content_type is set accordingly.

        Args:
            obj: a protobuf message, or a dict packed as a google.protobuf.Struct.

        Raises:
            google.protobuf.json_format.ParseError: a dict can't be a Struct.
        """
        if isinstance(obj, dict):
            if not self.has_content_type():
                self.content_type = ContentType.JSON
            obj = pb.ParseDict(obj, Struct())
        elif not self.has_content_type():
            self.content_type = ContentType.PROTOBUF

        if self.content_type == ContentType.JSON:
            json = pb.MessageToJson(obj, indent=0, always_print_fields_with_no_presence=True)
            self.body = json.encode("utf-8")
        else:
            self.body = obj.SerializeToString()

    def unpack(self, schema: type[Any] = dict) -> Any:
        """Deserialize the body, with the message's content_type (PROTOBUF if unset).

        Args:
            schema: the protobuf message class, or dict for a google.protobuf.Struct as a dict.

        Returns:
            A new `schema` with the body's content.

        Raises:
            google.protobuf.message.DecodeError: a PROTOBUF body isn't a `schema`.
            google.protobuf.json_format.ParseError: a JSON body isn't a `schema`.
        """
        obj = Struct() if schema is dict else schema()
        if self.content_type == ContentType.JSON:
            pb.Parse(self.body, obj)
        else:
            obj.ParseFromString(self.body)

        if schema is dict:
            return pb.MessageToDict(obj, always_print_fields_with_no_presence=True)
        return obj
