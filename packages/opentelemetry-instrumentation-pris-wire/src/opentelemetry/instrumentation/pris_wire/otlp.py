"""OTLP/HTTP export of traces and metrics, plus the pris-wire instrumentation, in one call.

Needs the otlp extra: opentelemetry-instrumentation-pris-wire[otlp].
"""

from __future__ import annotations

import os
from collections.abc import Callable

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor

Shutdown = Callable[[], None]


def setup_telemetry(
    otlp_endpoint: str,
    service_name: str = "",
    default_service_name: str = "unknown_service",
) -> Shutdown:
    """Export traces and metrics over OTLP/HTTP and instrument pris-wire.

    The other OTEL_* environment variables (resource attributes, headers, ...) still apply.

    Args:
        otlp_endpoint: the collector's base URL, e.g. "http://otel-collector:4318"; traces go to
            <endpoint>/v1/traces and metrics to <endpoint>/v1/metrics. Empty: nothing is set
            up and the OpenTelemetry API stays a no-op.
        service_name: the service.name resource attribute; by default OTEL_SERVICE_NAME, else
            `default_service_name`.
        default_service_name: the name used when neither is set.

    Returns:
        A function that flushes and stops the export; call it before the process exits.
    """
    if not otlp_endpoint:
        return lambda: None

    endpoint = otlp_endpoint.rstrip("/")
    name = service_name or os.environ.get("OTEL_SERVICE_NAME") or default_service_name
    resource = Resource.create({SERVICE_NAME: name})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint + "/v1/traces")))
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint + "/v1/metrics")),
        ],
    )
    return install(tracer_provider, meter_provider)


def install(tracer_provider: TracerProvider, meter_provider: MeterProvider) -> Shutdown:
    """Make the providers global and instrument pris-wire with them.

    Args:
        tracer_provider: the SDK tracer provider, with its span processors.
        meter_provider: the SDK meter provider, with its metric readers.

    Returns:
        A function that removes the instrumentation and shuts both providers down.
    """
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    instrumentor = PrisWireInstrumentor()
    instrumentor.instrument(tracer_provider=tracer_provider, meter_provider=meter_provider)

    def shutdown() -> None:
        instrumentor.uninstrument()
        tracer_provider.shutdown()
        meter_provider.shutdown()

    return shutdown
