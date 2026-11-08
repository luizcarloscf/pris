"""OpenTelemetry tracing and metrics for pris-wire's Channel.publish, Channel.consume and
ServiceProvider.serve."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from opentelemetry.instrumentation.instrumentor import (  # type: ignore[attr-defined]
    BaseInstrumentor,
)
from opentelemetry.instrumentation.pris_wire._propagation import extract
from opentelemetry.instrumentation.pris_wire._wrappers import Telemetry
from opentelemetry.instrumentation.pris_wire.package import _instruments
from opentelemetry.instrumentation.pris_wire.version import __version__
from opentelemetry.instrumentation.utils import unwrap
from wrapt import wrap_function_wrapper

__all__ = ["PrisWireInstrumentor", "extract", "__version__"]


class PrisWireInstrumentor(BaseInstrumentor):
    """Instruments pris-wire.

    `instrument(**kwargs)` wraps Channel.publish, Channel.consume and ServiceProvider.serve;
    `uninstrument()` removes the wrappers. The keyword arguments of `instrument` are:

    Args:
        tracer_provider: the TracerProvider to use; by default the global one.
        meter_provider: the MeterProvider to use; by default the global one.
        publish_hook: called as `hook(span, message)` inside the publish span, after the trace
            context was injected and right before the message is sent.
        consume_hook: called as `hook(span, message)` inside the receive span, once
            Channel.consume returned a message.
        request_hook: called as `hook(span, request)` inside the server span of
            ServiceProvider.serve, before the service function runs.
        response_hook: called as `hook(span, reply)` inside the server span, once the reply is
            final.
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs: Any) -> None:
        telemetry = Telemetry(
            tracer_provider=kwargs.get("tracer_provider"),
            meter_provider=kwargs.get("meter_provider"),
            publish_hook=kwargs.get("publish_hook"),
            consume_hook=kwargs.get("consume_hook"),
            request_hook=kwargs.get("request_hook"),
            response_hook=kwargs.get("response_hook"),
        )
        wrap_function_wrapper("pris_wire.core.channel", "Channel.publish", telemetry.publish)
        wrap_function_wrapper("pris_wire.core.channel", "Channel.consume", telemetry.consume)
        wrap_function_wrapper("pris_wire.rpc.service_provider", "ServiceProvider.serve",
                              telemetry.serve)

    def _uninstrument(self, **kwargs: Any) -> None:
        from pris_wire.core.channel import Channel
        from pris_wire.rpc.service_provider import ServiceProvider

        unwrap(Channel, "publish")
        unwrap(Channel, "consume")
        unwrap(ServiceProvider, "serve")
