# pris-common

Code shared by the PRIS services: fetching camera calibrations from [pris-calibration-server](../../services/pris-calibration-server/) and frame transformations from [pris-frame-transformation](../../services/pris-frame-transformation/), at startup. It holds what more than one service needs and isn't messaging ([pris-wire](../pris-wire/README.md)) or message schemas ([pris-msgs](../pris-msgs/README.md)). A high-level introduction, with runnable examples, is in the [documentation](../../docs/content/libraries/pris-common.md).

```shell
pip install "pris-common @ git+https://github.com/luizcarloscf/pris@pris-common-v0.1.0#subdirectory=packages/pris-common"
```

pris-common depends on pris-msgs and pris-wire; a project that installs them from git tags needs the same kind of source for each.

## Modules

Arguments, return values and errors are in each function's docstring.

| Import | Does |
|---|---|
| `pris_common.calibrations.fetch_calibrations` | requests the calibrations of the given cameras and waits for the reply; returns them by camera id |
| `pris_common.transformations.fetch_transformations` | requests the transformations between the given (source, target) frames and waits for the reply; returns them by pair |
| `pris_common.rpc.call` | publishes any request and waits for its reply; both functions above are built on it |

## fetch_calibrations

- A service calls it once, at startup, with the cameras of its options: `fetch_calibrations(channel, options.camera_ids)`. If it raises, the service logs the error and exits; Kubernetes restarts it until pris-calibration-server answers. A new calibration is picked up at the next restart.
- One request for every camera, on `CalibrationServer.GetCalibration` by default. The server answers NOT_FOUND to the whole request when any camera is unknown, which raises `RuntimeError`, as does a reply that misses a camera; no reply within `timeout` (5 s by default) raises `socket.timeout`.
- It consumes the channel until the reply arrives and drops any other message, so call it before subscribing to anything else on that channel.
- The reply queue is private to the channel and stays until the channel closes; only replies ever reach it.

## fetch_transformations

- The same at startup, for fixed transformations such as from the world to a camera: `fetch_transformations(channel, [(1000, 2)])`. One request for every pair, on `FrameTransformation.GetTransformation` by default.
- The reply is each transformation as it is now; one that changes, such as a marker's, is watched on its `FrameTransformation.<source>.<target>` topic instead.
- pris-frame-transformation answers NOT_FOUND, naming the pair, when a pair has no route; that, a reply that misses a pair, or no reply raise as in `fetch_calibrations`, and the same rule applies: call it before subscribing.

## call

- `call(channel, request, topic, timeout=5.0)` publishes `request` (a protobuf message) on `topic` with a private reply queue and consumes the channel until the reply with the same correlation id arrives, dropping anything else.
- It returns the reply `Message` when its status is OK; `reply.unpack(ReplyType)` gives the content. Any other status raises `RuntimeError` with the topic and the status; no reply within `timeout` raises `socket.timeout`.
- For one-off requests at startup, like the two functions above; a service that makes requests while consuming its topics needs its own loop, since `call` drops what isn't its reply.

## Development

From the repository root, with a broker running (`make broker-up`): `make test` and `make lint`. The tests use a real broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`), each on a topic of its own; `ServiceProvider`s answer as the calibration and transformation servers. To test another Python version: `uv run --isolated --python 3.10 pytest packages/pris-common`.
