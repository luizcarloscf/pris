from __future__ import annotations

import traceback
from typing import Any, Callable

from google.protobuf.json_format import ParseError

from ..core import Channel, Logger, Status, StatusCode, Subscription
from ..core.message import Message
from ..core.utils import assert_type
from .context import Context
from .interceptor import Interceptor


class ServiceProvider(object):
    """Serves requests: calls a function for each message received on a delegated topic and
    publishes its reply."""

    log = Logger("ServiceProvider", Logger.DEBUG)

    def __init__(self, channel: Channel) -> None:
        """Create a provider that serves on `channel`.

        Args:
            channel: the channel to receive requests and publish replies with.

        Raises:
            TypeError: `channel` isn't a Channel.
        """
        assert_type(channel, Channel, "channel")
        self._channel = channel
        self._services: dict[str, Callable[[Message], tuple[Message, bool]]] = {}
        self._interceptors_before: list[Callable[[Context], None]] = []
        self._interceptors_after: list[Callable[[Context], None]] = []
        self._subscriptions: list[Subscription] = []

    def delegate(self, topic: str, function: Callable[[Any, Context], Any],
                 request_type: type[Any], reply_type: type[Any]) -> None:
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
        if any(topic == s.name for s in self._subscriptions):
            raise RuntimeError(
                "Service on topic '{}' was already delegated".format(topic))

        self.log.debug("New service registered '{}'", topic)
        subscription = Subscription(self._channel, name=topic)
        self._subscriptions.append(subscription)
        wrapped = self.wrap(function, request_type, reply_type)
        self._services[subscription.id] = wrapped

    def add_interceptor(self, interceptor: Interceptor) -> None:
        """Run an interceptor's before_call and after_call around every request.

        Args:
            interceptor: an Interceptor, or any object with before_call and after_call methods.

        Raises:
            TypeError: `interceptor` has neither method.
        """
        itype = type(interceptor)
        if not hasattr(itype, "before_call") and \
           not hasattr(itype, "after_call"):
            raise TypeError("Interceptors must implement the Interceptor"
                            "concept or derive from the Interceptor class")
        self._interceptors_before.append(interceptor.before_call)
        self._interceptors_after.append(interceptor.after_call)

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
        try:
            service = self._services[message.subscription_id or ""]
        except KeyError as error:
            why = "Cannot serve message with subscription_id='{}'".format(
                message.subscription_id)
            raise RuntimeError(why) from error

        reply, timeouted = service(message)
        if reply.has_topic() and not timeouted:
            self._channel.publish(reply)

    def run(self) -> None:
        """Serve requests forever, blocking the current thread."""
        self.log.info("Listening for requests")
        while True:
            self.serve(self._channel.consume())

    def wrap(self, function: Callable[[Any, Context], Any], request_type: type[Any],
             reply_type: type[Any]) -> Callable[[Message], tuple[Message, bool]]:
        """Wrap a service function into one that builds the reply of a request.

        Args:
            function: the service function, as in delegate.
            request_type: the protobuf class of the requests.
            reply_type: the protobuf class of the replies.

        Returns:
            A function that takes a request and returns its reply and whether its deadline has
            passed. The reply's status is OK with the packed result, the Status the function
            returned, FAILED_PRECONDITION for a request that isn't a `request_type`,
            INTERNAL_ERROR if the function raised, or DEADLINE_EXCEEDED.
        """

        def safe_call(*args: Any) -> Any:
            try:
                result = function(*args)
                assert_type(result, (Status, reply_type), "function result")
                return result
            except Exception:
                return Status(
                    code=StatusCode.INTERNAL_ERROR,
                    why="Service throwed exception:\n{}".format(
                        traceback.format_exc()),
                )

        def run_interceptors(interceptors: list[Callable[[Context], None]],
                             *args: Any) -> None:
            for interceptor in interceptors:
                try:
                    interceptor(*args)
                except Exception:
                    trace = traceback.format_exc()
                    self.log.error("Interceptor throwed exception:\n{}", trace)

        def wrapper(request: Message) -> tuple[Message, bool]:
            reply = request.create_reply()
            context = Context(request, reply)

            run_interceptors(self._interceptors_before, context)

            if not request.deadline_exceeded():
                try:
                    arg = request.unpack(request_type)
                    result = safe_call(arg, context)
                    if isinstance(result, Status):
                        reply.status = result
                    else:
                        reply.pack(result)
                        reply.status = Status(code=StatusCode.OK)
                except ParseError:
                    why = "Expected request type '{}' but received " \
                        "something else" \
                        .format(request_type.DESCRIPTOR.full_name)
                    reply.status = Status(StatusCode.FAILED_PRECONDITION, why)
                except Exception:
                    trace = traceback.format_exc()
                    self.log.error("Unexpected error\n{}", trace)
                    reply.status = Status(StatusCode.INTERNAL_ERROR, trace)

            timeouted = request.deadline_exceeded()
            if timeouted:
                reply.status = Status(StatusCode.DEADLINE_EXCEEDED)

            run_interceptors(self._interceptors_after, context)

            return reply, timeouted

        return wrapper
