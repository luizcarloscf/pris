# pris-wire

Publish/subscribe and request/reply for PRIS over RabbitMQ (AMQP 0-9-1), built on [py-amqp](https://github.com/celery/py-amqp). A high-level introduction, with runnable examples, is in the [documentation](../../docs/content/libraries/pris-wire.md).

```shell
pip install "pris-wire @ git+https://github.com/luizcarloscf/pris@pris-wire-v1.0.0#subdirectory=packages/pris-wire"
```

## Modules

| Import | Does |
|---|---|
| `pris_wire.core.Channel` | a connection to the broker: `publish`, `consume`, `consume_for`, `consume_until`, `consume_ready`, `ack`, `reject` |
| `pris_wire.core.Subscription` | a queue bound to topics: private (exclusive) without a name, shared by replicas with one; `arguments`, `prefetch`, `manual_ack` |
| `pris_wire.core.Message` | a body and its properties; `pack`/`unpack` protobuf messages or dicts, `create_reply`, `deadline_exceeded` |
| `pris_wire.core.Status`, `StatusCode` | the result of a request, sent in the `rpc-status` header |
| `pris_wire.core.ContentType` | `PROTOBUF` or `JSON`, how a body is serialized |
| `pris_wire.core.Logger` | colored logging with `str.format` arguments; `LOG_LEVEL` sets every logger's level |
| `pris_wire.rpc.ServiceProvider` | serves functions on topics: `delegate`, `serve`, `should_serve`, `run` |
| `pris_wire.rpc.Interceptor`, `LogInterceptor` | code run before and after every request; `LogInterceptor` logs duration and status |

`src/pris_wire/core/wire/wire.proto` (`pris.wire`) defines `StatusCode`, `Status` and `ContentType`; it ships in the wheel next to its generated code.

On the broker:

- `Channel` declares the topic exchange `pris`; a topic is the routing key.
- A private queue is exclusive and a shared one durable, both auto-delete: RabbitMQ 4 refuses transient queues that aren't exclusive.
- A `Channel` belongs to one thread. Deliveries are kept in a queue, because `py-amqp` can dispatch them during `publish`.

## Development

From the repository root, with a broker running (`make broker-up`):

```shell
make proto # regenerate src/pris_wire/core/wire/wire_pb2.py/.pyi after editing wire.proto
make test
make lint
```

`make proto` runs `make -C packages/pris-wire proto`, which compiles `wire.proto` with `pris_msgs.utils.build` and the protoc bundled in `grpcio-tools`. The tests connect to `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`). To test another Python version: `uv run --isolated --python 3.10 pytest packages/pris-wire`.