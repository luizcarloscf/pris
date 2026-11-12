# pris-aruco-localization

A camera alone gives a poor pose for a small or distant marker: its depth is uncertain, and its orientation can flip. `pris-aruco-localization` combines every camera that sees a marker at the same capture instant, from the corners pris-aruco-detector finds, and publishes each marker's pose in the world. With the four cameras of the LabVISIO, a 0.2 m marker is localized within a few millimeters and about a degree.

!!! info "New to multi-view geometry?"

    - [Pose estimation of ArUco markers](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html): one camera, and why it can flip;
    - [Triangulation](https://en.wikipedia.org/wiki/Triangulation_(computer_vision)): points from several views, the starting point of the pose;
    - [Kabsch algorithm](https://en.wikipedia.org/wiki/Kabsch_algorithm): the rigid fit of the marker to the triangulated corners.

## Where it fits

```mermaid
flowchart LR
  detector("pris-aruco-detector") -->|"ArUco.#lt;id#gt;.Detection"| localization("pris-aruco-localization")
  localization -.->|"CalibrationServer.GetCalibration, at startup"| calibration("pris-calibration-server")
  localization -->|"ArUco.FrameTransformations"| frames("pris-frame-transformation")
  localization -.->|"FrameTransformation.GetTransformation, at startup"| frames
```

Detections are grouped by their capture instant, not by arrival: those within `sync.tolerance` of the oldest one waiting are one instant, solved as soon as every camera sent, or after `sync.max_delay` with the cameras that did. With two cameras:

```mermaid
sequenceDiagram
  participant C0 as ArUco.0.Detection
  participant C1 as ArUco.1.Detection
  participant L as pris-aruco-localization
  participant F as ArUco.FrameTransformations
  C0->>L: captured at t
  C1->>L: captured at t + 5 ms
  Note over L: every camera sent t
  L->>F: the poses at t, from both cameras
  C0->>L: captured at t + 100 ms
  Note over L: camera 1 is silent for max_delay
  L->>F: the poses at t + 100 ms, from camera 0
```

## Localizing a marker

The service needs [pris-calibration-server](pris-calibration-server.md), which serves the cameras' calibrations: start it as its page shows, with the local broker of `make broker-up`. Then start the service from the repository root:

```shell
cat > /tmp/options.json <<END
{"broker_uri": "amqp://guest:guest@localhost:5672", "reference_frame": "1000", "frame_id_offset": "100",
 "markers": {"0": 0.2}, "camera_ids": ["0", "1", "2", "3"], "sync": {"tolerance": 0.03, "max_delay": 0.1},
 "max_camera_error": 5.0, "min_cameras": 1, "validity": 1.0}
END
uv run --project services/pris-aruco-localization pris-aruco-localization /tmp/options.json
```

With pris-aruco-detector publishing the cameras' detections, listen to the poses in another terminal:

```python
from pris_msgs.camera_pb2 import FrameTransformations
from pris_msgs.utils.tensor import to_array
from pris_wire.core import Channel, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
Subscription(channel).subscribe("ArUco.FrameTransformations")

for tf in channel.consume(timeout=10.0).unpack(FrameTransformations).tfs:
    print(tf.source, "->", tf.target, to_array(tf.tf)[:3, 3].round(3))
# 100 -> 1000 [ 0.5 -0.3  0. ]
channel.close()
```

The pose comes back as `FrameTransformation` 100 → 1000: the marker's frame, `100 + id`, to the world. pris-frame-transformation takes these poses as edges of its graph, so `FrameTransformation.100.<camera>` follows the marker in any camera.

One instance serves the whole space, even with several worlds (see [Several worlds](pris-frame-transformation.md#several-worlds)).

## Reference

How a pose is computed, the capture instants, the options, telemetry, accuracy and development are in the service's [README](https://github.com/luizcarloscf/pris/tree/main/services/pris-aruco-localization#readme).
