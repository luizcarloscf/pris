# pris-aruco-localization

Localizes ArUco markers in the world. It takes the corners that pris-aruco-detector finds in each camera, groups the detections of the same capture instant, and computes one pose per marker from every camera that sees it. A single camera gives a poor pose for a small or distant marker: depth is uncertain, and the marker's orientation can flip; combining cameras fixes both (see [Accuracy](#accuracy)). A high-level introduction, with a runnable example, is in the [documentation](../../docs/content/services/pris-aruco-localization.md).

## Interface

| | Topic | Message |
|---|---|---|
| Consumes | `ArUco.<id>.Detection` | `pris.vision.ObjectAnnotations`, from pris-aruco-detector |
| Publishes | `ArUco.FrameTransformations` | `pris.vision.FrameTransformations` |
| Calls | `CalibrationServer.GetCalibration`, at startup | through `pris_common.calibrations.fetch_calibrations` |
| Calls | `FrameTransformation.GetTransformation`, at startup, for cameras of another world | through `pris_common.transformations.fetch_transformations` |

One `ArUco.FrameTransformations` per capture instant, even when no marker is localized (an empty list). Each localized marker is one `FrameTransformation`:

| Field | Contents |
|---|---|
| `source` | the marker's frame: `frame_id_offset + marker id` (`100 + id` by default) |
| `target` | `reference_frame` (1000, the world) |
| `tf` | 4×4, marker to reference; its last column is the marker's center |
| `expiration` | the capture instant plus `validity` |

The message's `created_at` is the mean capture instant of the detections it combines. The marker frame is OpenCV's: origin at the center of the marker, x to the right, y up, z out of the printed face; its corners are top-left (−L/2, L/2, 0), top-right (L/2, L/2, 0), bottom-right (L/2, −L/2, 0) and bottom-left (−L/2, −L/2, 0), the order pris-aruco-detector publishes them. pris-frame-transformation takes these poses as dynamic edges.

## How it works

At startup it fetches the calibrations of `camera_ids` with `pris_common.calibrations.fetch_calibrations` and turns each into a camera with its extrinsic from `reference_frame`. For a camera calibrated in another world, it asks pris-frame-transformation for one with `pris_common.transformations.fetch_transformations`. A missing calibration or extrinsic makes it exit, and Kubernetes restarts it. A new calibration is picked up at the next restart. Each camera's intrinsics are scaled to the resolution of its detections.

It keeps every camera's detections, so it runs as one instance: replicas would each get their own copy instead of sharing the work. Run one for the whole space, with the cameras of every world: the cameras at a door are combined in one pose, and each marker has the single parent pris-frame-transformation accepts.

- **Capture instants.** `ArucoLocalization.step` consumes the cameras' detection topics. Detections whose capture instants are within `sync.tolerance` of the instant's first one belong to it, one per camera; an instant is solved once every camera has sent, or `sync.max_delay` after its first detection arrived, with the cameras that have. A detection older than the last solved instant is dropped. The cameras capture on a shared clock grid and `created_at` is the hardware capture instant, so only detections of the same tick are combined: keep the tolerance below half the frame period.
- **A pose**, for each configured marker of an instant:
  1. **Undistort.** Each camera's corners become normalized image coordinates.
  2. **Candidates.** With two or more cameras, the 4 corners are triangulated (linear DLT, one batched SVD) and the marker is fitted to them (Kabsch, never a reflection). Each camera alone also gives its two IPPE solutions, the marker and its flipped twin. The candidate with the lowest reprojection error over all cameras wins.
  3. **Refine.** Levenberg–Marquardt over the pose's 6 degrees of freedom, minimizing the reprojection error of every corner in every camera, in pixels, updated in the marker frame to keep rotation and translation decoupled.
  4. **Outliers.** While more than one camera is left and the worst one is off by more than `max_camera_error` pixels (RMS), it is dropped (wrong corners, another marker with the same id, a bad calibration) and the pose is computed again.
  5. **Accept.** The pose is published if enough cameras remain (`min_cameras`) and its RMS error is within `max_error`.

| Module | Does |
|---|---|
| `geometry.py` | cameras from calibrations, undistortion, triangulation, Kabsch, IPPE candidates, Levenberg–Marquardt, outlier cameras |
| `service.py` | `ArucoLocalization`: the loop (group the detections by capture instant, solve, publish), the spans, and its static methods `camera_id`, `observations`, `transformation` and `accepted` |
| `main.py` | the startup: options, telemetry, the calibrations, then `run` |

## Options

`pris-aruco-localization [options.json]`, by default `/etc/pris-aruco-localization/options.json`. The fields are described in [`conf/options.proto`](src/pris_aruco_localization/conf/options.proto) and their defaults, those of the image on a cluster, are in [`etc/conf/options.json`](etc/conf/options.json): `broker_uri` (`rabbitmq.pris`), `telemetry` (to `otel-collector.pris`; an empty `otlp_endpoint` turns it off), and:

- `camera_ids`: the cameras whose detections are combined, from any world (0 to 3); their calibrations are fetched at startup.
- `markers`: marker id → side length in meters. The length is the black square, without the white border: a wrong length puts the marker at a wrong distance. Other markers are ignored.
- `reference_frame`: the frame the poses are given in (1000, the world). A camera of another world gets its extrinsic from pris-frame-transformation, which needs that camera in its own `camera_ids`.
- `sync`: `tolerance` (30 ms) and `max_delay` (100 ms).
- `max_camera_error`, `max_error` (0 publishes every pose) and `min_cameras`, the thresholds above; `validity`, how long a pose stays valid.

`LOG_LEVEL=DEBUG` logs the outlier cameras.

## Telemetry

One span `localize` per instant, linked to the publish of each detection it combines, with `pris.aruco_localization.cameras`, `.markers` (localized), `.discarded` and `.delay` (seconds from the capture instant to the solution), and one `marker` event per localized marker with its cameras, the rejected ones and its error. The pose carries no quality on the wire: only these events do. The messaging metrics come from [opentelemetry-instrumentation-pris-wire](../../packages/opentelemetry-instrumentation-pris-wire/README.md).

## Accuracy

Measured with the four LabVISIO calibrations (cameras about 2.8 m high, 5 m from the center of the room), a 0.2 m marker in random poses facing the cameras, and Gaussian noise on the corners:

| Corner noise | Cameras | Position (median / 95%) | Orientation (median / 95%) |
|---|---|---|---|
| 0.5 px | 1 | 54 mm / 218 mm | 2.05° / 127° (flips) |
| 0.5 px | 2 | 1.6 mm / 5.0 mm | 0.79° / 1.60° |
| 0.5 px | 4 | 1.1 mm / 2.1 mm | 0.60° / 1.06° |
| 1.0 px | 4 | 2.3 mm / 4.3 mm | 1.19° / 2.12° |

A pose takes about 1.5 ms per marker. Real cameras add calibration error, blur and timing, which these numbers don't include. A marker seen edge-on by its only camera has nearly collinear corners and isn't localized; other cameras make it work.

## Running

It needs pris-calibration-server, and pris-aruco-detector for real detections. With a local broker (`make broker-up`), from the repository root:

```shell
cat > /tmp/options.json <<EOF
{"broker_uri": "amqp://guest:guest@localhost:5672", "reference_frame": "1000", "frame_id_offset": "100",
 "markers": {"0": 0.2}, "camera_ids": ["0", "1", "2", "3"], "sync": {"tolerance": 0.03, "max_delay": 0.1},
 "max_camera_error": 5.0, "min_cameras": 1, "validity": 1.0}
EOF
uv run --project services/pris-aruco-localization pris-aruco-localization /tmp/options.json
```

The image, built with `make image` in this folder or `make image SERVICE=pris-aruco-localization` at the repository root, runs with the cluster's options; on one host, mount your own over `/etc/pris-aruco-localization/options.json` (see [Docker images](../../docs/content/deployment/docker.md)). On Kubernetes, [`k8s/pris-aruco-localization/`](../../k8s/pris-aruco-localization/) runs it as one instance (see [Kubernetes](../../docs/content/deployment/kubernetes.md)).

## Development

An independent project: its `pyproject.toml` takes the PRIS libraries from their git tags, and `uv.lock` pins them; pris-common depends on pris-msgs and pris-wire, so `override-dependencies` pins those to the same tags, pris-msgs with its `opencv` extra (see [Libraries from git tags](../../docs/content/deployment/git-dependencies.md)). From the repository root, with a broker running, `make test` and `make lint` run its tests and mypy too; in this folder, `uv run pytest` and `uv run mypy src`. The tests build synthetic detections from the calibrations of `calibrations/labvisio/` and use a real broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`), each on topics of its own. `make proto` regenerates `conf/options_pb2.py/.pyi` after editing `options.proto`.
