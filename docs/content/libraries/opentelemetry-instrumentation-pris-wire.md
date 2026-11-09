# OpenTelemetry instrumentation

`opentelemetry-instrumentation-pris-wire` gives every component of PRIS traces and metrics with no change to its code: it wraps [pris-wire](pris-wire.md)'s `Channel.publish`, `Channel.consume` and `ServiceProvider.serve`, and carries the trace context inside each message. A request then shows up as one trace, from the caller through the service and back, in any OpenTelemetry backend such as Jaeger.

!!! info "New to OpenTelemetry?"

    These pages from the official documentation explain what this package produces:

    - [Concepts](https://opentelemetry.io/docs/concepts/): [traces](https://opentelemetry.io/docs/concepts/signals/traces/), [metrics](https://opentelemetry.io/docs/concepts/signals/metrics/) and [context propagation](https://opentelemetry.io/docs/concepts/context-propagation/);
    - [OpenTelemetry for Python](https://opentelemetry.io/docs/languages/python/): the SDK, [manual instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/) and [zero-code instrumentation](https://opentelemetry.io/docs/zero-code/python/) with `opentelemetry-instrument`;
    - the semantic conventions the spans and metrics follow: [messaging spans](https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/), [RabbitMQ](https://opentelemetry.io/docs/specs/semconv/messaging/rabbitmq/) and [RPC spans](https://opentelemetry.io/docs/specs/semconv/rpc/rpc-spans/).

## What it records

| pris-wire call | Span | Metrics |
|---|---|---|
| `Channel.publish` | `publish {topic}`, PRODUCER | messages sent, operation duration |
| `Channel.consume`, when a message arrives | `receive {topic}`, CLIENT, in the producer's trace (or under the current span, if any) | messages consumed, operation duration |
| `ServiceProvider.serve` | `{topic}`, SERVER, child of the request's receive span | call duration, with the reply's status code |

Replies are named `(reply)` instead of their random queue names, and consume timeouts record nothing, so traces and metrics stay readable.

## One trace per request

The trace context travels inside each message, so a request, its handling and its reply are one trace. The example runs as is, with a broker on `localhost` (`make broker-up` in this repository) and the package installed with its `otlp` extra (see the [README](https://github.com/luizcarloscf/pris/tree/main/packages/opentelemetry-instrumentation-pris-wire#readme)). It keeps the spans in memory, so no collector is needed, and one channel plays both the service and the caller:

```python
from google.protobuf.wrappers_pb2 import FloatValue
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.instrumentation.pris_wire.otlp import install
from pris_wire.core import Channel, Message, Subscription
from pris_wire.rpc import ServiceProvider

spans = InMemorySpanExporter()                          # keeps the spans in memory
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(spans))
install(tracer_provider, MeterProvider())               # instruments pris-wire

channel = Channel("amqp://guest:guest@localhost:5672")
provider = ServiceProvider(channel)
provider.delegate("Math.Double", lambda value, context: FloatValue(value=2 * value.value),
                  request_type=FloatValue, reply_type=FloatValue)
replies = Subscription(channel)

channel.publish(Message(content=FloatValue(value=21), reply_to=replies), topic="Math.Double")
provider.serve(channel.consume(timeout=1.0))            # the service answers
print(channel.consume(timeout=1.0).unpack(FloatValue).value)   # 42.0

for span in spans.get_finished_spans():
    print(span.name)
# publish Math.Double
# receive Math.Double
# publish (reply)
# Math.Double
# receive (reply)
print(len({span.context.trace_id for span in spans.get_finished_spans()}))   # 1: one trace
```

The spans are listed as they finish: the service's span, `Math.Double`, ends after it published the reply.

When you consume messages yourself, `extract(message)` gives the context to start your own span under the message's receive span: `tracer.start_as_current_span("process", context=extract(message))`.

## In a service

A service sends its traces and metrics to an [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) with one call at startup, and flushes them before it exits:

```python
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry

shutdown = setup_telemetry("http://otel-collector:4318", default_service_name="my-service")
try:
    pass                                                # run the service
finally:
    shutdown()
```

An empty endpoint turns telemetry off. Without changing code, `opentelemetry-instrument python service.py` finds the instrumentation by itself and takes its settings from the `OTEL_*` environment variables.

## Reference

The spans' attributes, the metrics, hooks, propagation and development are in the package's [README](https://github.com/luizcarloscf/pris/tree/main/packages/opentelemetry-instrumentation-pris-wire#readme).
