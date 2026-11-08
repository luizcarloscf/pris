"""The wrappers PrisWireInstrumentor installs on pris-wire's classes."""

from __future__ import annotations

import logging
import time
import weakref
from contextvars import ContextVar
from timeit import default_timer
from collections.abc import Callable
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.instrumentation.pris_wire import _semconv as sc
from opentelemetry.instrumentation.pris_wire._propagation import extract, inject
from opentelemetry.instrumentation.pris_wire.version import __version__
from opentelemetry.trace import Link, Span, SpanKind, Status, StatusCode

_logger = logging.getLogger(__name__)

PublishHook = Callable[[Span, Any], None]
ConsumeHook = Callable[[Span, Any], None]
RequestHook = Callable[[Span, Any], None]
ResponseHook = Callable[[Span, Any], None]

_SERVER_ERRORS = frozenset({
    "UNKNOWN", "DEADLINE_EXCEEDED", "UNIMPLEMENTED", "INTERNAL_ERROR",
})

_current_reply: ContextVar[dict[str, Any] | None] = ContextVar(
    "pris_wire_current_reply", default=None)


class _ReplyInterceptor:
    """Hands the final reply of a request to the serve wrapper running it."""

    def before_call(self, context: Any) -> None:
        pass

    def after_call(self, context: Any) -> None:
        slot = _current_reply.get()
        if slot is not None:
            slot["reply"] = context.reply


Attributes = dict[str, Any]


def _call_hook(hook: Callable[..., None] | None, *args: Any) -> None:
    if hook is None:
        return
    try:
        hook(*args)
    except Exception:
        _logger.exception("pris_wire instrumentation hook failed")


def _server_attributes(channel: Any) -> Attributes:
    host = getattr(getattr(channel, "connection", None), "host", None)
    if not isinstance(host, str) or not host:
        return {}
    address, _, port = host.rpartition(":")
    if not address or not port.isdigit():
        return {sc.SERVER_ADDRESS: host}
    return {sc.SERVER_ADDRESS: address, sc.SERVER_PORT: int(port)}


def _bind_publish(message: Any, topic: str | None = None) -> tuple[Any, str | None]:
    return message, topic


class Telemetry:
    """The tracer, metric instruments and hooks the wrappers share."""

    def __init__(
        self,
        tracer_provider: trace.TracerProvider | None = None,
        meter_provider: metrics.MeterProvider | None = None,
        publish_hook: PublishHook | None = None,
        consume_hook: ConsumeHook | None = None,
        request_hook: RequestHook | None = None,
        response_hook: ResponseHook | None = None,
    ) -> None:
        scope = "opentelemetry.instrumentation.pris_wire"
        self.tracer = trace.get_tracer(scope, __version__, tracer_provider)
        meter = metrics.get_meter(scope, __version__, meter_provider)
        self.operation_duration = meter.create_histogram(
            sc.MESSAGING_CLIENT_OPERATION_DURATION,
            unit="s",
            description="Duration of messaging operation initiated by a producer or "
                        "consumer client.",
            explicit_bucket_boundaries_advisory=sc.DURATION_BUCKETS,
        )
        self.sent_messages = meter.create_counter(
            sc.MESSAGING_CLIENT_SENT_MESSAGES,
            unit="{message}",
            description="Number of messages producer attempted to send to the broker.",
        )
        self.consumed_messages = meter.create_counter(
            sc.MESSAGING_CLIENT_CONSUMED_MESSAGES,
            unit="{message}",
            description="Number of messages that were delivered to the application.",
        )
        self.server_call_duration = meter.create_histogram(
            sc.RPC_SERVER_CALL_DURATION,
            unit="s",
            description="Measures the duration of inbound remote procedure calls.",
            explicit_bucket_boundaries_advisory=sc.DURATION_BUCKETS,
        )
        self.publish_hook = publish_hook
        self.consume_hook = consume_hook
        self.request_hook = request_hook
        self.response_hook = response_hook
        self._reply_interceptor = _ReplyInterceptor()
        self._providers: weakref.WeakSet[Any] = weakref.WeakSet()

    def publish(self, wrapped: Callable[..., Any], instance: Any,
                args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        message, topic = _bind_publish(*args, **kwargs)
        routing_key = topic if topic else (message.topic if message.has_topic() else None)
        if not routing_key:
            return wrapped(*args, **kwargs)

        exchange = getattr(instance, "_exchange", "")
        is_reply = message.has_status()
        destination = sc.REPLY_DESTINATION if is_reply else routing_key

        metric_attributes: Attributes = {
            sc.MESSAGING_SYSTEM: sc.RABBITMQ,
            sc.MESSAGING_OPERATION_TYPE: sc.SEND,
            sc.MESSAGING_OPERATION_NAME: sc.PUBLISH,
            sc.MESSAGING_DESTINATION_NAME: "{}:{}".format(exchange, destination),
            **_server_attributes(instance),
        }
        if is_reply:
            metric_attributes[sc.MESSAGING_DESTINATION_TEMPORARY] = True

        span_attributes: Attributes = {
            **metric_attributes,
            sc.MESSAGING_RABBITMQ_ROUTING_KEY: routing_key,
        }
        if message.has_correlation_id():
            span_attributes[sc.MESSAGING_MESSAGE_CONVERSATION_ID] = \
                "{:X}".format(message.correlation_id)
        if message.has_body():
            span_attributes[sc.MESSAGING_MESSAGE_BODY_SIZE] = len(message.body)

        with self.tracer.start_as_current_span(
            "{} {}".format(sc.PUBLISH, destination),
            kind=SpanKind.PRODUCER,
            attributes=span_attributes,
        ) as span:
            inject(message)
            _call_hook(self.publish_hook, span, message)
            start = default_timer()
            try:
                return wrapped(*args, **kwargs)
            except Exception as error:
                error_type = type(error).__qualname__
                span.set_attribute(sc.ERROR_TYPE, error_type)
                metric_attributes[sc.ERROR_TYPE] = error_type
                raise
            finally:
                self.operation_duration.record(max(default_timer() - start, 0),
                                               metric_attributes)
                self.sent_messages.add(1, metric_attributes)

    def consume(self, wrapped: Callable[..., Any], instance: Any,
                args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        start_time = time.time_ns()
        start = default_timer()
        exchange = getattr(instance, "_exchange", "")
        attributes: Attributes = {
            sc.MESSAGING_SYSTEM: sc.RABBITMQ,
            sc.MESSAGING_OPERATION_TYPE: sc.RECEIVE,
            sc.MESSAGING_OPERATION_NAME: sc.RECEIVE,
            **_server_attributes(instance),
        }

        try:
            message = wrapped(*args, **kwargs)
        except TimeoutError:
            raise
        except Exception as error:
            attributes[sc.ERROR_TYPE] = type(error).__qualname__
            span = self.tracer.start_span(sc.RECEIVE, kind=SpanKind.CLIENT,
                                          start_time=start_time, attributes=attributes)
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.end()
            self.operation_duration.record(max(default_timer() - start, 0), attributes)
            raise

        duration = max(default_timer() - start, 0)
        is_reply = message.has_status()
        destination = sc.REPLY_DESTINATION if is_reply else message.topic
        attributes[sc.MESSAGING_DESTINATION_NAME] = "{}:{}".format(exchange, destination)
        if is_reply:
            attributes[sc.MESSAGING_DESTINATION_TEMPORARY] = True

        span_attributes: Attributes = {
            **attributes,
            sc.MESSAGING_RABBITMQ_ROUTING_KEY: message.topic,
        }
        if message.has_correlation_id():
            span_attributes[sc.MESSAGING_MESSAGE_CONVERSATION_ID] = \
                "{:X}".format(message.correlation_id)
        if message.has_body():
            span_attributes[sc.MESSAGING_MESSAGE_BODY_SIZE] = len(message.body)

        producer_context = extract(message)
        producer = trace.get_current_span(producer_context).get_span_context()
        ambient = trace.get_current_span().get_span_context().is_valid
        span = self.tracer.start_span(
            "{} {}".format(sc.RECEIVE, destination),
            kind=SpanKind.CLIENT,
            context=None if ambient else producer_context,
            attributes=span_attributes,
            links=[Link(producer)] if producer.is_valid else None,
        )
        with trace.use_span(span, end_on_exit=True):
            _call_hook(self.consume_hook, span, message)
        inject(message, trace.set_span_in_context(span))

        self.operation_duration.record(duration, attributes)
        self.consumed_messages.add(1, attributes)
        return message

    def serve(self, wrapped: Callable[..., Any], instance: Any,
              args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        message = args[0] if args else kwargs["message"]
        if instance not in self._providers:
            instance.add_interceptor(self._reply_interceptor)
            self._providers.add(instance)

        method = message.topic if instance.should_serve(message) else sc.OTHER_METHOD
        attributes: Attributes = {
            sc.RPC_SYSTEM_NAME: sc.PRIS_WIRE,
            sc.RPC_METHOD: method,
        }

        slot: dict[str, Any] = {}
        token = _current_reply.set(slot)
        start = default_timer()
        try:
            with self.tracer.start_as_current_span(
                method if method != sc.OTHER_METHOD else sc.PRIS_WIRE,
                context=extract(message),
                kind=SpanKind.SERVER,
                attributes=attributes,
            ) as span:
                _call_hook(self.request_hook, span, message)
                try:
                    return wrapped(*args, **kwargs)
                except Exception as error:
                    attributes[sc.ERROR_TYPE] = type(error).__qualname__
                    span.set_attribute(sc.ERROR_TYPE, attributes[sc.ERROR_TYPE])
                    raise
                finally:
                    reply = slot.get("reply")
                    if reply is not None:
                        self._record_reply(span, reply, attributes)
                        _call_hook(self.response_hook, span, reply)
        finally:
            _current_reply.reset(token)
            self.server_call_duration.record(max(default_timer() - start, 0), attributes)

    @staticmethod
    def _record_reply(span: Span, reply: Any, attributes: Attributes) -> None:
        if not reply.has_status():
            return
        code = reply.status.code.name
        attributes[sc.RPC_RESPONSE_STATUS_CODE] = code
        span.set_attribute(sc.RPC_RESPONSE_STATUS_CODE, code)
        if reply.status.ok():
            return
        attributes.setdefault(sc.ERROR_TYPE, code)
        span.set_attribute(sc.ERROR_TYPE, attributes[sc.ERROR_TYPE])
        if code in _SERVER_ERRORS:
            span.set_status(Status(StatusCode.ERROR, reply.status.why or code))
