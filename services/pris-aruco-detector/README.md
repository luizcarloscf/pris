# pris-aruco-detector

Detects [ArUco](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html) markers on the cameras' frames, and publishes, for each frame, the id and the four corners of every marker it finds, in pixels. It only detects: it computes no pose and needs no calibration. Turning corners into positions in the space, by combining the cameras that see the same marker, is pris-aruco-localization's job. A high-level introduction, with a runnable example, is in the [documentation](../../docs/content/services/pris-aruco-detector.md).

## Interface

| | Topic | Message |
|---|---|---|
| Consumes | `CameraGateway.<id>.Frame` | `pris.vision.Image` |
| Publishes | `ArUco.<id>.Detection` | `pris.vision.ObjectAnnotations` |

One detection per processed frame of camera `<id>`, even when no marker is in it: an empty list means nothing was seen, while no message means the frame wasn't processed.

| Field | Contents |
|---|---|
| `objects[].id` | the marker's id in the dictionary |
| `objects[].label` | the same id, as a string |
| `objects[].score` | always 1: ArUco has no confidence, a decoded marker passed its code check |
| `objects[].region.vertices` | the 4 corners in pixels: top-left, top-right, bottom-right, bottom-left |
| `resolution` | the frame's width and height |
| `frame_id` | the camera id |

The detection's `created_at` is the frame's, which the gateway sets to the instant of the capture, so the detections of several cameras can be matched by time, to the millisecond (the precision of `created_at` on the wire). A frame that can't be decoded (no data, only a `uri`, or bad bytes) publishes nothing, and is logged as a warning.

## How it works

- **Newest frame per camera.** Each turn waits for a frame, takes every other frame already received, and processes only the newest one of each camera; the older ones are dropped and counted. A slow detector skips frames instead of falling behind, and no camera starves the others.
- **Replicas split the frames.** Every replica consumes the same named queue, `queue_name`, so the broker spreads the frames between them: add replicas when one CPU can't keep up with the cameras.
- **Choosing cameras.** `camera_ids` limits the service to some cameras; empty means every `CameraGateway.*.Frame`. Give each group of cameras, with its own replicas, a different `queue_name`.
- **Detection** is OpenCV's `cv2.aruco.ArucoDetector` on the grayscale image, with the dictionary and corner refinement of the options, whose names are OpenCV's.

| Module | Does |
|---|---|
| `detector.py` | `MarkerDetector`: an Image, decoded to gray pixels with `pris_msgs.utils.image.to_array`, to ObjectAnnotations |
| `service.py` | `ArucoDetectorService`: the subscription, the per-turn loop, the spans, the publishing, and its static methods `camera_id` and `latest_per_camera` |
| `main.py` | the startup: options, OpenCV's threads, telemetry, then `run` |

## Options

`pris-aruco-detector [options.json]`, by default `/etc/pris-aruco-detector/options.json`. The fields are described in [`conf/options.proto`](src/pris_aruco_detector/conf/options.proto) and their defaults, those of the image on a cluster, are in [`etc/conf/options.json`](etc/conf/options.json): `broker_uri` (`rabbitmq.pris`), `camera_ids`, `queue_name` (`ArUco.Detector`), `telemetry` (to `otel-collector.pris`; an empty `otlp_endpoint` turns it off) and `detector`:

- `dictionary` must match the printed markers: markers of other dictionaries aren't seen at all.
- `corner_refinement`: `CORNER_REFINE_SUBPIX` gives the most accurate corners, which pose estimation and triangulation need.
- `cpu_threads`: 1 by default, matching the 1 CPU of each replica on Kubernetes: scale with replicas rather than threads. 0 keeps OpenCV's default, one thread per core (`cv2.setNumThreads(0)` would make OpenCV sequential, so 0 doesn't call it).

`LOG_LEVEL=DEBUG` also logs the dropped frames.

## Telemetry

One CONSUMER span `process CameraGateway.<id>.Frame` per processed frame, child of the gateway's publish, with `pris.aruco_detector.camera_id`, `pris.aruco_detector.markers` (the markers found) and `pris.aruco_detector.dropped` (the camera's older frames dropped for this one). It is marked ERROR when the frame can't be decoded. The detection's publish is its child; the messaging metrics come from [opentelemetry-instrumentation-pris-wire](../../packages/opentelemetry-instrumentation-pris-wire/README.md).

## Running

With a local broker (`make broker-up`), from the repository root:

```shell
cat > /tmp/options.json <<EOF
{"broker_uri": "amqp://guest:guest@localhost:5672", "queue_name": "ArUco.Detector"}
EOF
uv run --project services/pris-aruco-detector pris-aruco-detector /tmp/options.json
```

The image, built with `make image` in this folder or `make image SERVICE=pris-aruco-detector` at the repository root, runs with the cluster's options; on one host, mount your own over `/etc/pris-aruco-detector/options.json` (see [Docker images](../../docs/content/deployment/docker.md)). On Kubernetes, [`k8s/labvisio/pris-aruco-detector/`](../../k8s/labvisio/pris-aruco-detector/) runs it with replicas (see [Kubernetes](../../docs/content/deployment/kubernetes.md)).

## Development

An independent project: its `pyproject.toml` takes the PRIS libraries from their git tags, and `uv.lock` pins them. From the repository root, with a broker running, `make test` and `make lint` run its tests and mypy too; in this folder, `uv run pytest` and `uv run mypy src`. The tests render markers with OpenCV and use a real broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`), each on topics of its own. `make proto` regenerates `conf/options_pb2.py/.pyi` after editing `options.proto`.
