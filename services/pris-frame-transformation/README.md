# pris-frame-transformation

Keeps the graph of the coordinate frames of the space and gives the transformation between any two of them: published to whoever listens, or on request. The graph holds two kinds of edges: static ones, the camera extrinsics from pris-calibration-server, and dynamic ones, every transformation published on a `*.FrameTransformations` topic, such as the markers of pris-aruco-localization. Like ROS's tf2 buffer, it only composes the edges it is given: combining several estimates of the same thing is the job of whoever publishes the edge. A high-level introduction, with a runnable example, is in the [documentation](../../docs/content/services/pris-frame-transformation.md).

## Interface

| | Topic | Message |
|---|---|---|
| Consumes | `#.FrameTransformations` | `pris.vision.FrameTransformations`: dynamic edges |
| Consumes | `BrokerEvents.Consumers` | `pris.common.ConsumerList`, from pris-broker-events: who listens |
| Publishes | `FrameTransformation.<source>[.<hint>...].<target>` | `pris.vision.FrameTransformation`, whenever it changes |
| Serves | `FrameTransformation.GetTransformation` | `pris.vision.GetTransformationRequest` (pairs, without hints) → `pris.vision.GetTransformationReply`, in their order |

- **Watching.** Subscribe to `FrameTransformation.<source>.<target>` and the service publishes the transformation that maps `<source>` coordinates to `<target>` coordinates, every time its route or edges change. It learns about subscriptions from pris-broker-events, and computes only the topics that have consumers. A new subscriber gets the current value at once. Extra ids are frames the route must go through, in order: `FrameTransformation.107.1000.2` is 107 → 1000 → 2. A transformation without a route (an unknown frame, an expired edge) isn't published until it has one again.
- **Each published transformation** has `source` and `target`, the first and last ids of the topic; `tf`, the 4×4 product of the edges along the route; and `expiration`, the earliest of its edges, absent if none expires. The message's `created_at` is the latest instant of its dynamic edges, such as a marker's capture instant, or the publish time if the route is all static.
- **Requesting.** `GetTransformation` answers a list of pairs, without hints, as `pris_common.transformations.fetch_transformations` asks. A pair without a route makes the reply `NOT_FOUND`, naming it, with no transformations.

## How it works

At startup it fetches the calibrations of `camera_ids` with `pris_common.calibrations.fetch_calibrations`, before subscribing to anything; if one is missing, or an extrinsic isn't a 4×4 matrix, it exits, and Kubernetes restarts it. Then, after each batch of messages (one `consume` plus every message already waiting), it applies the new edges, expires the old ones, updates the watched topics from the latest consumer list, serves the requests, and publishes the watched transformations that changed. It waits at most until the next edge expires.

- **Static edges.** Every extrinsic of each calibration becomes a static edge, from its `source` frame to the camera, whatever that frame is: a camera calibrated in two worlds links both. Static edges never expire, and a dynamic message can't replace one: it is ignored, with a warning logged once per pair. A new calibration is picked up at the next restart.
- **Dynamic edges.** Each transformation of a `*.FrameTransformations` message, with the message's `created_at` as its instant and its own `expiration`. A newer message for the same pair replaces the edge; expired edges are removed; a transformation without `expiration` stays until replaced.
- **Routes.** The route with the fewest edges; between equally short ones, static edges and then lower frame ids win, so the same graph always gives the same route. Edges are traversed both ways, the inverse computed when needed.
- **Startup order.** pris-broker-events publishes the consumers only when a binding changes. The service subscribes to `BrokerEvents.Consumers` before its other topics: its own new bindings are such changes, so the full list arrives right after, and subscribers already waiting are served at once.

It runs as one instance: every instance would publish the same transformations and answer the same requests.

| Module | Does |
|---|---|
| `graph.py` | `FrameGraph`: edges, expiration, routes, composition, a version per edge |
| `watch.py` | `Watches`: the `FrameTransformation.*` topics with consumers, and which changed since last published |
| `service.py` | `FrameTransformationService`: the loop, the request, the spans, and its static methods `static_edges`, `dynamic_edges` and `to_message` |
| `main.py` | the startup: options, telemetry, the calibrations, then `run` |

## Options

`pris-frame-transformation [options.json]`, by default `/etc/pris-frame-transformation/options.json`. The fields are described in [`conf/options.proto`](src/pris_frame_transformation/conf/options.proto) and their defaults, those of the image on a cluster, are in [`etc/conf/options.json`](etc/conf/options.json): `broker_uri` (`rabbitmq.pris`), `camera_ids` (0 to 3; with none, the graph has only dynamic edges) and `telemetry` (to `otel-collector.pris`; an empty `otlp_endpoint` turns it off). It logs each camera's static edges and each topic it starts or stops watching.

## Telemetry

One span `update` per batch that brought transformations or published something, linked to the `*.FrameTransformations` messages of the batch, with `pris.frame_transformation.edges` (the edges set) and `pris.frame_transformation.published` (the topics published); the publishes are its children. The request gets the SERVER span of [opentelemetry-instrumentation-pris-wire](../../packages/opentelemetry-instrumentation-pris-wire/README.md); `NOT_FOUND` is the caller's error and doesn't mark it as failed.

## Running

It needs pris-calibration-server (for the static edges) and pris-broker-events (to know who listens). With a local broker (`make broker-up`) and both running, from the repository root:

```shell
cat > /tmp/options.json <<EOF
{"broker_uri": "amqp://guest:guest@localhost:5672", "camera_ids": ["0", "1", "2", "3"]}
EOF
uv run --project services/pris-frame-transformation pris-frame-transformation /tmp/options.json
```

## Development

An independent project: its `pyproject.toml` takes the PRIS libraries from their git tags, and `uv.lock` pins them. pris-common depends on pris-msgs and pris-wire, so `override-dependencies` pins those to the same tags as the service (see [Libraries from git tags](../../docs/content/deployment/git-dependencies.md)). From the repository root, with a broker running, `make test` and `make lint` run its tests and mypy too; in this folder, `uv run pytest` and `uv run mypy src`. The tests use a real broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`), each on topics of its own, and the calibrations of `calibrations/labvisio/`. `make proto` regenerates `conf/options_pb2.py/.pyi` after editing `options.proto`.
