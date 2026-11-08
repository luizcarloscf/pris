from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor
from opentelemetry.instrumentation.pris_wire import otlp


def test_disabled_without_endpoint():
    shutdown = otlp.setup_telemetry("")
    assert not PrisWireInstrumentor().is_instrumented_by_opentelemetry
    shutdown()


def test_endpoint_and_default_service_name(monkeypatch):
    installed = {}
    endpoints = []

    def record(exporter):
        def build(endpoint):
            endpoints.append(endpoint)
            return exporter(endpoint=endpoint)
        return build

    monkeypatch.setattr(otlp, "OTLPSpanExporter", record(otlp.OTLPSpanExporter))
    monkeypatch.setattr(otlp, "OTLPMetricExporter", record(otlp.OTLPMetricExporter))
    monkeypatch.setattr(otlp, "install",
                        lambda tracer_provider, meter_provider: installed.update(
                            tracer=tracer_provider, meter=meter_provider) or (lambda: None))
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    otlp.setup_telemetry("http://collector:4318/", default_service_name="my-service")

    assert endpoints == ["http://collector:4318/v1/traces", "http://collector:4318/v1/metrics"]
    assert installed["tracer"].resource.attributes["service.name"] == "my-service"
    installed["tracer"].shutdown()
    installed["meter"].shutdown(timeout_millis=1000)


def test_service_name_precedence(monkeypatch):
    names = []
    monkeypatch.setattr(otlp, "install", lambda tracer_provider, meter_provider: names.append(
        tracer_provider.resource.attributes["service.name"]) or (lambda: None))

    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    otlp.setup_telemetry("http://collector:4318")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "from-env")
    otlp.setup_telemetry("http://collector:4318", default_service_name="default")
    otlp.setup_telemetry("http://collector:4318", service_name="from-options",
                         default_service_name="default")

    assert names == ["unknown_service", "from-env", "from-options"]
