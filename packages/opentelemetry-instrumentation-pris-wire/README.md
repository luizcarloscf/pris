# opentelemetry-instrumentation-pris-wire

OpenTelemetry tracing and metrics for [pris-wire](../pris-wire/README.md): `Channel.publish`, `Channel.consume` and `ServiceProvider.serve`. pris-wire has no OpenTelemetry dependency; this package wraps it from the outside, like the other `opentelemetry-instrumentation-*` packages. Its module is `opentelemetry.instrumentation.pris_wire`. A high-level introduction, with runnable examples, is in the [documentation](../../docs/content/libraries/opentelemetry-instrumentation-pris-wire.md).

```shell
pip install "opentelemetry-instrumentation-pris-wire[otlp] @ git+https://github.com/luizcarloscf/pris@opentelemetry-instrumentation-pris-wire-v0.1.0#subdirectory=packages/opentelemetry-instrumentation-pris-wire"
```

| Extra | Adds |
|---|---|
| `instruments` | pris-wire itself |
| `otlp` | the SDK and the OTLP/HTTP exporters, for `opentelemetry.instrumentation.pris_wire.otlp` |

## Modules

Arguments, return values and errors are in each function's docstring.

| Import | Does |
|---|---|
| `PrisWireInstrumentor` | `instrument(tracer_provider=, meter_provider=, publish_hook=, consume_hook=, request_hook=, response_hook=)` and `uninstrument()`; also found by `opentelemetry-instrument` through the `opentelemetry_instrumentor` entry point `pris_wire` |
| `extract(message)` | the trace context a message carries: after `Channel.consume`, its receive span; to parent the spans that process it |
| `otlp.setup_telemetry(endpoint, service_name=, default_service_name=)` | OTLP/HTTP export of traces and metrics, global providers and the instrumentation, in one call; an empty endpoint sets up nothing |
| `otlp.install(tracer_provider, meter_provider)` | the same with providers you build, such as in-memory ones in tests |

Instrument before the program starts publishing or serving.

## Spans

| Operation | Span name | Kind | Parent |
|---|---|---|---|
| `Channel.publish` | `publish {topic}` | PRODUCER | the current span |
| `Channel.consume`, when a message arrives | `receive {topic}` | CLIENT | the current span if there is one, else the producer's span; always a link to the producer |
| `ServiceProvider.serve` | `{topic}` | SERVER | the request's receive span (the caller's span if the request wasn't received by an instrumented `consume`) |

- Messaging attributes (publish and receive): `messaging.system=rabbitmq`, `messaging.operation.type` and `.name`, `messaging.destination.name` (`{exchange}:{topic}`), `messaging.rabbitmq.destination.routing_key`, `messaging.message.conversation_id` (the correlation id), `messaging.message.body.size`, `server.address` and `server.port`.
- RPC attributes (serve): `rpc.system.name=pris_wire`, `rpc.method`, `rpc.response.status_code` (the `StatusCode` name), and `error.type` when the reply isn't `OK`.
- A SERVER span is an error only for server-side failures: `INTERNAL_ERROR` (a service function that raises included), `DEADLINE_EXCEEDED`, `UNIMPLEMENTED` and `UNKNOWN`. Codes that blame the caller, such as `NOT_FOUND` or `INVALID_ARGUMENT`, leave its status unset, as the RPC conventions ask.
- The service function, the spans it creates and the publication of the reply all happen inside the SERVER span.
- A receive span joins the producer's trace when nothing is current, as in a service's main loop or `ServiceProvider.run()`: otherwise every consumed message would start a one-span trace. The messaging conventions link consumers to producers by default and leave the receive span's parent open; a single message is always received here, never a batch, so the producer's context can be the parent. With a current span, the receive span is its child, as the conventions' default.
- Processing nests under the receive span: once `consume` returns a message, the instrumentation writes the receive span's context into its metadata, so `extract(message)` and `ServiceProvider.serve` start their spans as its children. Each hop then reads publish → receive → processing in the trace. The producer is still in the receive span's link.

## Metrics

| Metric | Type | Unit | Recorded by |
|---|---|---|---|
| `messaging.client.sent.messages` | counter | `{message}` | publish, every attempt |
| `messaging.client.consumed.messages` | counter | `{message}` | consume |
| `messaging.client.operation.duration` | histogram | `s` | publish and consume |
| `rpc.server.call.duration` | histogram | `s` | serve |

Histograms use the bucket boundaries the semantic conventions recommend (5 ms to 10 s). Metric attributes are the low-cardinality subset of the span attributes: no routing key, no correlation id.

## Bounded cardinality

- Replies go to per-client queues with random names (`host/1A2B…`): their spans are named `publish (reply)` and `receive (reply)`, with `messaging.destination.temporary=true`. The queue name only appears in the span's routing key attribute, never in metrics.
- A request on a topic with no delegated function gets `rpc.method=_OTHER`.
- Consume timeouts (`socket.timeout`) record nothing, so polling loops don't flood the traces.
- A receive span starts when the message arrives, not when `consume` was called: a consumer waiting in its main loop would otherwise get a receive span as long as the wait, starting before its parent. The wait is still in `messaging.client.operation.duration`, which measures the whole call.

## Propagation and hooks

- The trace context is written to and read from `Message.metadata`, which pris-wire sends as AMQP headers, by the global propagator: W3C `traceparent` and baggage by default, or what `OTEL_PROPAGATORS` selects. `ServiceProvider` continues the trace by itself; when you consume messages yourself, parent your processing with `extract(message)`.
- Hooks receive the span and run inside it. An exception in a hook is logged and ignored, so hooks never break messaging.
- Reply statuses are captured by a pris-wire interceptor, added to each `ServiceProvider` the first time it serves a request. After `uninstrument()` it stays attached but does nothing.
- Get tracers with `trace.get_tracer()` when you need them, not in a module-level variable: such a tracer stays bound to the first provider it sees.

## Development

From the repository root, with a broker running (`make broker-up`): `make test` and `make lint`. The tests use in-memory exporters and a real broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`), each on a topic of its own. mypy checks it by module name (`mypy -p opentelemetry.instrumentation.pris_wire`): it is a namespace package, and its `pris_wire` folder would clash with pris-wire's by path. To test another Python version: `uv run --isolated --python 3.10 pytest packages/opentelemetry-instrumentation-pris-wire`.
