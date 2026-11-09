# pris-calibration-server

Serves the calibration of each camera on `CalibrationServer.GetCalibration`: intrinsics, distortion, and the extrinsic transformations from the world frame. Services that turn pixels into positions, or the reverse, ask it for the calibrations of their cameras, usually with [`pris_common.calibrations.fetch_calibrations`](../../packages/pris-common/README.md), and never read calibration files themselves. A high-level introduction, with a runnable example, is in the [documentation](../../docs/content/services/pris-calibration-server.md).

## Request

| Topic | Request | Reply |
|---|---|---|
| `CalibrationServer.GetCalibration` | `pris.vision.GetCalibrationRequest`: `ids`, the camera ids | `pris.vision.GetCalibrationReply`: `calibrations`, in the order of `ids` |

If any id is unknown, the reply is `NOT_FOUND`, naming it, and holds no calibrations. Several instances can run: they serve the same files, and the broker gives each request to one of them, since the request queue is shared.

## Calibration files

At startup the server loads every `<id>.json` in `calibrations_path`, each a `pris.vision.CameraCalibration` in protobuf JSON; other files and subdirectories are ignored.

| Field | Contents |
|---|---|
| `id` | the camera id, equal to the file name without `.json`; a string, as int64 values are in protobuf JSON |
| `calibratedAt` | when the calibration was made (RFC 3339) |
| `error` | the reprojection error, in pixels |
| `resolution` | the image size the intrinsics refer to |
| `intrinsic` | the 3×3 camera matrix, row-major |
| `distortion` | the 1×5 distortion coefficients (k1, k2, p1, p2, k3) |
| `extrinsic` | transformations from a `source` frame to the camera, the `target` (`tf`: 4×4, row-major); frame 1000 is the world |

It refuses to start if `calibrations_path` isn't a directory, holds no `*.json` file, or has a file that is unreadable, invalid, or whose `id` isn't its name: a bad calibration stops the deployment instead of being served. Write every field, zeros included: a missing field parses as 0, so a missing `id` reads as camera 0 and is refused for not matching the file name. Calibrations are read once; a change needs a restart.

The calibrations of each site are kept in [`calibrations/<site>/`](../../calibrations/), and the tests check every one of them: their ids, matrix shapes, and proper rotations.

## Options

`pris-calibration-server [options.json]`, by default `/etc/pris-calibration-server/options.json`. The fields are described in [`conf/options.proto`](src/pris_calibration_server/conf/options.proto) and their defaults are in [`etc/conf/options.json`](etc/conf/options.json): `broker_uri`, `calibrations_path` (`/etc/calibrations`, where the calibrations are mounted) and `telemetry`.

## Telemetry

With `telemetry.otlp_endpoint` set, each request is a SERVER span `CalibrationServer.GetCalibration`, child of the caller's span, with the requested ids in `pris.calibration_server.ids`; camera ids are few, so they are fine as an attribute. `NOT_FOUND` is the caller's error, so it leaves the span's status unset. The RPC and messaging metrics come from [opentelemetry-instrumentation-pris-wire](../../packages/opentelemetry-instrumentation-pris-wire/README.md).

## Running

With a local broker (`make broker-up`) and the repository's calibrations, from the repository root:

```shell
cat > /tmp/options.json <<EOF
{"broker_uri": "amqp://guest:guest@localhost:5672", "calibrations_path": "calibrations/labvisio"}
EOF
uv run --project services/pris-calibration-server pris-calibration-server /tmp/options.json
```

## Development

An independent project: its `pyproject.toml` takes pris-msgs, pris-wire and opentelemetry-instrumentation-pris-wire from their git tags, and `uv.lock` pins them. From the repository root, with a broker running, `make test` and `make lint` run its tests and mypy too; in this folder, `uv run pytest` and `uv run mypy src`. The tests use a real broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`). `make proto` regenerates `conf/options_pb2.py/.pyi` after editing `options.proto`.
