# pris-aruco-detector

ArUco markers are square black-and-white codes, each with an id, that a camera can find in an image. Stuck on a robot or on the floor, they give the space reference points. `pris-aruco-detector` finds them on the frames of every camera and publishes, for each frame, the id and the four corners of every marker it sees, in pixels. Turning those corners into positions, by combining the cameras that see the same marker, is the next service's job.

!!! info "New to ArUco markers?"

    - [Detection of ArUco markers](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html): OpenCV's tutorial on the dictionaries, the detection and the corners;
    - [ArUco marker generator](https://chev.me/arucogen/): print markers of the dictionary the service looks for, `DICT_4X4_50` by default.

## Where it fits

```mermaid
flowchart LR
  gateway("pris-camera-gateway<br>one per camera") -->|"CameraGateway.#lt;id#gt;.Frame"| detector("pris-aruco-detector<br>replicas")
  detector -->|"ArUco.#lt;id#gt;.Detection"| localization("pris-aruco-localization")
```

## Detecting markers

With the local broker of `make broker-up`, start the service from the repository root:

```shell
cat > /tmp/options.json <<END
{"broker_uri": "amqp://guest:guest@localhost:5672", "queue_name": "ArUco.Detector"}
END
uv run --project services/pris-aruco-detector pris-aruco-detector /tmp/options.json
```

With [pris-camera-gateway](pris-camera-gateway.md) publishing frames, listen to the detections of every camera in another terminal:

```python
from pris_msgs.image_pb2 import ObjectAnnotations
from pris_wire.core import Channel, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
Subscription(channel).subscribe("ArUco.*.Detection")

message = channel.consume(timeout=10.0)
for marker in message.unpack(ObjectAnnotations).objects:
    print(message.topic, marker.id, [(round(v.x), round(v.y)) for v in marker.region.vertices])
# ArUco.0.Detection 7 [(400, 250), (519, 250), (519, 369), (400, 369)]
# ArUco.0.Detection 3 [(100, 80), (219, 80), (219, 199), (100, 199)]
channel.close()
```

The corners come in OpenCV's order, top-left first, clockwise. A frame without markers still gets a detection, with no objects, and the detection keeps the frame's capture instant, so the detections of several cameras can be matched by time. Several replicas share the frames of a named queue, and each one processes only the newest frame of each camera, skipping the older ones instead of falling behind.

## Reference

The detection's fields, the options (dictionary, corner refinement, threads), telemetry and development are in the service's [README](https://github.com/luizcarloscf/pris/tree/main/services/pris-aruco-detector#readme).
