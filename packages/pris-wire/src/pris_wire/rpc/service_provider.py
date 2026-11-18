from __future__ import annotations

import traceback
from typing import Any, Callable

from google.protobuf.json_format import ParseError
from google.protobuf.message import DecodeError

from ..core import Channel, Logger, Status, StatusCode, Subscription
from ..core.message import Message
from ..core.utils import assert_type
from .context import Context
from .interceptor import Interceptor

ServiceFunction = Callable[[Any, Context], Any]


class ServiceProvider:
    """Serves requests: calls a function for each message received on a delegated topic and
    publishes its reply."""

    def __init__(self, channel: Channel) -> None:
        """Create a provider that serves on `channel`.

        Args:
            channel: the channel to receive requests and publish replies with.

        Raises:
            TypeError: `channel` isn't a Channel.
        """
        assert_type(channel, Channel, "channel")
        self.log = Logger("ServiceProvider")
        self._channel = channel
        self._topics: set[str] = set()
        self._services: dict[str, tuple[ServiceFunction, type[Any], type[Any]]] = {}
        self._interceptors: list[Interceptor] = []

    def delegate(
        self, topic: str, function: ServiceFunction, request_type: type[Any], reply_type: type[Any]
    ) -> None:
        """Serve the requests published to a topic with a function.

        The topic gets a named queue, so replicas of a service split its requests.

        Args:
            topic: the topic to serve, e.g. "MyService.GetConfig".
            function: called with the unpacked request and the Context; returns a `reply_type`
                for an OK reply, or a Status for an error.
            request_type: the protobuf class of the requests.
            reply_type: the protobuf class of the replies.

        Raises:
            TypeError: `topic` isn't a str.
            RuntimeError: `topic` is already delegated.
        """
        assert_type(topic, str, "topic")
        if topic in self._topics:
            raise RuntimeError("Service on topic '{}' was already delegated".format(topic))

        subscription = Subscription(self._channel, name=topic)
        self._topics.add(topic)
        self._services[subscription.id] = (function, request_type, reply_type)
        self.log.debug("New service registered '{}'", topic)

    def add_interceptor(self, interceptor: Interceptor) -> None:
        """Run an interceptor's before_call and after_call around every request.

        Args:
            interceptor: an Interceptor, or any object with before_call and after_call methods.

        Raises:
            TypeError: `interceptor` lacks before_call or after_call.
        """
        if not (
            callable(getattr(interceptor, "before_call", None))
            and callable(getattr(interceptor, "after_call", None))
        ):
            raise TypeError(
                "an interceptor needs before_call and after_call methods, got {}".format(
                    type(interceptor).__name__
                )
            )
        self._interceptors.append(interceptor)

    def should_serve(self, message: Message) -> bool:
        """Return True if `message` was received on a delegated topic."""
        return message.subscription_id in self._services

    def serve(self, message: Message) -> None:
        """Serve a request and publish its reply, unless its deadline has passed.

        Args:
            message: a message received on a delegated topic.

        Raises:
            RuntimeError: `message` wasn't received on a delegated topic (see should_serve).
        """
        if not self.should_serve(message):
            raise RuntimeError(
                "Cannot serve message with subscription_id='{}'".format(message.subscription_id)
            )

        reply, expired = self._reply(message, *self._services[message.subscription_id or ""])
        if reply.has_topic() and not expired:
            self._channel.publish(reply)

    def run(self) -> None:
        """Serve requests forever, blocking the current thread."""
        self.log.info("Listening for requests")
        while True:
            self.serve(self._channel.consume())

    def _reply(
        self,
        request: Message,
        function: ServiceFunction,
        request_type: type[Any],
        reply_type: type[Any],
    ) -> tuple[Message, bool]:
        """Build the reply of a request, and say whether its deadline has passed."""
        reply = request.create_reply()
        context = Context(request, reply)

        self._intercept("before_call", context)
        if not request.deadline_exceeded():
            reply.status = self._call(function, request_type, reply_type, context)
        expired = request.deadline_exceeded()
        if expired:
            reply.status = Status(StatusCode.DEADLINE_EXCEEDED)
        self._intercept("after_call", context)

        return reply, expired

    def _call(
        self,
        function: ServiceFunction,
        request_type: type[Any],
        reply_type: type[Any],
        context: Context,
    ) -> Status:
        """Call the service function and pack its result into the reply."""
        try:
            request = context.request.unpack(request_type)
        except (DecodeError, ParseError):
            return Status(
                StatusCode.FAILED_PRECONDITION,
                "Expected request type '{}' but received something else".format(
                    request_type.DESCRIPTOR.full_name
                ),
            )

        try:
            result = function(request, context)
            assert_type(result, (Status, reply_type), "function result")
            if isinstance(result, Status):
                return result
            context.reply.pack(result)
        except Exception:
            return Status(
                StatusCode.INTERNAL_ERROR,
                "Service raised an exception:\n{}".format(traceback.format_exc()),
            )
        return Status(StatusCode.OK)

    def _intercept(self, method: str, context: Context) -> None:
        """Run one method of every interceptor, logging the exceptions they raise."""
        for interceptor in self._interceptors:
            try:
                getattr(interceptor, method)(context)
            except Exception:
                self.log.error("Interceptor raised an exception:\n{}", traceback.format_exc())
