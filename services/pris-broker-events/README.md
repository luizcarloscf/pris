# pris-broker-events

Publishes, for every topic, the queues that consume it, on `BrokerEvents.Consumers`, and again whenever that changes. Programs use it to discover what is running: which cameras are online, whether a service serves a topic, whether anyone listens to a topic at all. A high-level introduction, with a runnable example, is in the [documentation](../../docs/content/services/pris-broker-events.md).

## Published

| Topic | Message |
|---|---|
| `BrokerEvents.Consumers` | `pris.common.ConsumerList`: `info`, from each binding (a topic, or a pattern such as `CameraGateway.*.Frame`) to the names of the queues bound to it |

Every queue is also bound to its own name, so request/reply services, whose queues are named after their topic, appear under that topic. The list is published only when it changes; a new subscriber's own subscription is a change, so it gets the list right after subscribing.

## How it works

1. At startup it subscribes to `binding.*` on the named queue `BrokerEvents`, then asks the broker's management API for every binding (`GET /api/bindings`) and keeps those from the exchange `pris` to a queue: each one is a consumer (queue) of a topic (routing key). Subscribing first means no binding falls between the two; one that comes both ways is kept once. If the API can't be reached, the service exits, and Kubernetes restarts it.
2. The broker publishes its own events through the [event exchange plugin](https://www.rabbitmq.com/docs/event-exchange) to `amq.rabbitmq.event`, which the broker's definitions bind to `pris` with the routing key `#`.
3. On each binding created or deleted from `pris` to a queue, it updates the list and publishes it. Other events, such as bindings between exchanges or on other exchanges, are ignored.

It runs as one instance: replicas would split the events of the shared queue. The queue is auto-delete, so it disappears while the service is down, and the initial query of the next start rebuilds the list.

| Module | Does |
|---|---|
| `management.py` | `fetch_bindings`, the management API query |
| `service.py` | `BrokerEvents`: the subscription, `load`, `handle` and `run`, and its static methods `consumers_from_bindings` (the initial list) and `apply_event` (one event applied to it) |
| `main.py` | the startup: options, telemetry, the bindings, then `run` |

## Broker

It needs the `rabbitmq_management` and `rabbitmq_event_exchange` plugins and the binding from `amq.rabbitmq.event` to `pris`. The broker of [`k8s/common/rabbitmq/`](../../k8s/common/rabbitmq/) has all three, and so does the local one of `make broker-up`, which runs with the same configuration.

## Options

`pris-broker-events [options.json]`, by default `/etc/pris-broker-events/options.json`. The fields are described in [`conf/options.proto`](src/pris_broker_events/conf/options.proto) and their defaults, those of the image on a cluster, are in [`etc/conf/options.json`](etc/conf/options.json): `broker_uri` (`rabbitmq.pris`), `broker_management_api` (`uri`, at `rabbitmq.pris`, and `timeout`) and `telemetry` (to `otel-collector.pris`; an empty `otlp_endpoint` turns it off). `broker_management_api.uri` carries the API's credentials: they never go to spans, but the options are logged at startup.

## Telemetry

- `GET /api/bindings` (CLIENT): the initial query, with the API's host and port, never the credentials of the URI.
- `process binding.created` or `process binding.deleted` (CONSUMER), for each event, with the binding's topic and queue (`pris.broker_events.binding.topic` and `.queue`), or `pris.broker_events.ignored=true`.
- From [opentelemetry-instrumentation-pris-wire](../../packages/opentelemetry-instrumentation-pris-wire/README.md): `receive binding.*` and `publish BrokerEvents.Consumers`, and the messaging metrics.

## Running

With a local broker (`make broker-up`), from the repository root:

```shell
cat > /tmp/options.json <<EOF
{"broker_uri": "amqp://guest:guest@localhost:5672",
 "broker_management_api": {"uri": "http://guest:guest@localhost:15672", "timeout": 5.0}}
EOF
uv run --project services/pris-broker-events pris-broker-events /tmp/options.json
```

The image, built with `make image` in this folder or `make image SERVICE=pris-broker-events` at the repository root, runs with the cluster's options; on one host, mount your own over `/etc/pris-broker-events/options.json` (see [Docker images](../../docs/content/deployment/docker.md)). On Kubernetes, [`k8s/labvisio/pris-broker-events/`](../../k8s/labvisio/pris-broker-events/) runs it (see [Kubernetes](../../docs/content/deployment/kubernetes.md)).

## Development

An independent project: its `pyproject.toml` takes the PRIS libraries from their git tags, and `uv.lock` pins them. From the repository root, with a broker running, `make test` and `make lint` run its tests and mypy too; in this folder, `uv run pytest` and `uv run mypy src`. The tests use the broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`) and its management API at `RABBITMQ_MANAGEMENT_URI` (default `http://guest:guest@localhost:15672`). `make proto` regenerates `conf/options_pb2.py/.pyi` after editing `options.proto`.
