# pris-aruco-localization

A camera alone gives a poor pose for a small or distant marker: its depth is uncertain, and its orientation can flip. `pris-aruco-localization` combines every camera that sees a marker at the same capture instant, from the corners pris-aruco-detector finds, and publishes each marker's pose in the world. With the four cameras of the LabVISIO, a 0.2 m marker is localized within a few millimeters and about a degree.

!!! info "New to multi-view geometry?"

    - [Pose estimation of ArUco markers](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html): one camera, and why it can flip;
    - [Triangulation](https://en.wikipedia.org/wiki/Triangulation_(computer_vision)): points from several views, the starting point of the pose;
    - [Kabsch algorithm](https://en.wikipedia.org/wiki/Kabsch_algorithm): the rigid fit of the marker to the triangulated corners.

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

In another terminal, listen to the poses:

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

In a third, stand in for pris-aruco-detector: project marker 0, on the floor at (0.5, −0.3), into the four cameras and publish what each one would detect, with the same capture instant (run it with `uv run --project services/pris-aruco-localization python detections.py`):

```python
import time

import cv2
import numpy as np
from pris_common.calibrations import fetch_calibrations
from pris_msgs.image_pb2 import ObjectAnnotations
from pris_wire.core import Channel, Message
from pris_aruco_localization.geometry import camera_from_calibration, marker_corners, transform

channel = Channel("amqp://guest:guest@localhost:5672")
cameras = [camera_from_calibration(calibration, 1000)
           for calibration in fetch_calibrations(channel, [0, 1, 2, 3]).values()]
pose = np.eye(4)
pose[:3, 3] = [0.5, -0.3, 0.0]                          # marker 0, on the floor

captured = time.time()                                  # every camera captures at this instant
for camera in cameras:
    rotation, _ = cv2.Rodrigues(camera.extrinsic[:3, :3])
    pixels, _ = cv2.projectPoints(transform(pose, marker_corners(0.2)), rotation,
                                  camera.extrinsic[:3, 3], camera.intrinsic, camera.distortion)
    detection = ObjectAnnotations(frame_id=camera.id)
    detection.resolution.width, detection.resolution.height = camera.width, camera.height
    marker = detection.objects.add(id=0, label="0", score=1.0)
    for x, y in pixels.reshape(4, 2):
        marker.region.vertices.add(x=float(x), y=float(y))
    message = Message(content=detection)
    message.created_at = captured
    channel.publish(message, topic="ArUco.{}.Detection".format(camera.id))
channel.close()
```

The pose comes back as `FrameTransformation` 100 → 1000: the marker's frame, `100 + id`, to the world. pris-frame-transformation takes these poses as edges of its graph, so `FrameTransformation.100.<camera>` follows the marker in any camera.

## Reference

How a pose is computed, the capture instants, the options, telemetry, accuracy and development are in the service's [README](https://github.com/luizcarloscf/pris/tree/main/services/pris-aruco-localization#readme).
