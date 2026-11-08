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

## Seeing the spans

Every example below runs as is, with a broker on `localhost` (`make broker-up` in this repository) and the package installed with its `otlp` extra (see the [README](https://github.com/luizcarloscf/pris/tree/main/packages/opentelemetry-instrumentation-pris-wire#readme)). They keep the spans in memory and print them, so no collector is needed:

```python
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.instrumentation.pris_wire.otlp import install
from pris_wire.core import Channel, Message, Subscription

spans = InMemorySpanExporter()
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(spans))
shutdown = install(tracer_provider, MeterProvider())

channel = Channel("amqp://guest:guest@localhost:5672")
subscription = Subscription(channel)
subscription.subscribe("Robot.0.Position")
channel.publish(Message(content=b"hello"), topic="Robot.0.Position")
channel.consume(timeout=1.0)
channel.close()

for span in spans.get_finished_spans():
    print(span.name, span.kind)
# publish Robot.0.Position SpanKind.PRODUCER
# receive Robot.0.Position SpanKind.CLIENT
shutdown()
```

## One trace per request

The caller's trace context travels in the request, so the service's span is its child, and the reply continues the same trace:

```python
from google.protobuf.wrappers_pb2 import FloatValue
from opentelemetry import trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.instrumentation.pris_wire.otlp import install
from pris_wire.core import Channel, Message, Subscription
from pris_wire.rpc import ServiceProvider

spans = InMemorySpanExporter()
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(spans))
shutdown = install(tracer_provider, MeterProvider())

channel = Channel("amqp://guest:guest@localhost:5672")
provider = ServiceProvider(channel)
provider.delegate("Math.Double", lambda value, context: FloatValue(value=2 * value.value),
                  request_type=FloatValue, reply_type=FloatValue)
replies = Subscription(channel)

with trace.get_tracer("caller").start_as_current_span("ask"):
    channel.publish(Message(content=FloatValue(value=21), reply_to=replies), topic="Math.Double")
    provider.serve(channel.consume(timeout=1.0))
    reply = channel.consume(timeout=1.0)
channel.close()

print(reply.unpack(FloatValue).value)                                  # 42.0
print(sorted(span.name for span in spans.get_finished_spans()))
# ['Math.Double', 'ask', 'publish (reply)', 'publish Math.Double', 'receive (reply)', 'receive Math.Double']
print(len({span.context.trace_id for span in spans.get_finished_spans()}))   # 1: one trace
shutdown()
```

When you consume messages yourself, `extract(message)` gives the message's receive span, to start your processing span as its child: `tracer.start_as_current_span("process", context=extract(message))`. Each hop then reads publish → receive → processing.

## In a service

A service exports to a [collector](https://opentelemetry.io/docs/collector/) over OTLP/HTTP with one call, at startup; an empty endpoint turns telemetry off:

```python
from opentelemetry.instrumentation.pris_wire.otlp import setup_telemetry

shutdown = setup_telemetry("", default_service_name="my-service")   # e.g. "http://otel-collector:4318"
try:
    pass                                                             # run the service
finally:
    shutdown()                                                       # flushes what is pending
```

Without changing code, `opentelemetry-instrument python service.py` finds the instrumentation through its entry point and takes its settings from the `OTEL_*` environment variables.

## Reference

The spans' attributes, the metrics, hooks, propagation and development are in the package's [README](https://github.com/luizcarloscf/pris/tree/main/packages/opentelemetry-instrumentation-pris-wire#readme).
