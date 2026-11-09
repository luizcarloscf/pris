# pris-frame-transformation

Where is a marker, in the coordinates of a camera? Where is camera 0, seen from camera 1? `pris-frame-transformation` keeps the graph of the coordinate frames of the space, and composes the transformation between any two of them, published to whoever listens or on request. Its edges come from the camera calibrations (static) and from the `*.FrameTransformations` other services publish, such as marker poses (dynamic).

!!! info "New to coordinate frames?"

    - [tf2 concepts](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Tf2.html): the ROS library this service resembles, a tree of frames and the transformations between them;
    - [Rigid transformations](https://en.wikipedia.org/wiki/Rigid_transformation): the 4×4 matrices `[R t; 0 1]` the edges hold.

## Watching and asking

The service needs [pris-calibration-server](pris-calibration-server.md) for the static edges and [pris-broker-events](pris-broker-events.md) to know who listens: start both as their pages show, with the local broker of `make broker-up`, then the service, from the repository root:

```shell
cat > /tmp/options.json <<END
{"broker_uri": "amqp://guest:guest@localhost:5672", "camera_ids": ["0", "1", "2", "3"]}
END
uv run --project services/pris-frame-transformation pris-frame-transformation /tmp/options.json
```

Subscribe to `FrameTransformation.<source>.<target>`, and the service publishes the transformation from `<source>` to `<target>` coordinates, at once and whenever it changes:

```python
from pris_msgs.camera_pb2 import FrameTransformation
from pris_msgs.utils.tensor import to_array
from pris_wire.core import Channel, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
Subscription(channel).subscribe("FrameTransformation.0.1")   # from camera 0 to camera 1

message = channel.consume(timeout=5.0)
tf = message.unpack(FrameTransformation)
print(tf.source, tf.target, to_array(tf.tf)[:3, 3].round(3))      # 0 1 [ 6.199 -2.176  5.365]
channel.close()
```

Or ask once, with [pris-common](../libraries/pris-common.md):

```python
from pris_msgs.utils.tensor import to_array
from pris_wire.core import Channel
from pris_common.transformations import fetch_transformations

channel = Channel("amqp://guest:guest@localhost:5672")
transformations = fetch_transformations(channel, [(1, 0)])
print(to_array(transformations[1, 0].tf)[:3, 3].round(3))       # [-6.337 -2.251  5.17 ]
channel.close()
```

Here both routes go through the world, frame 1000: camera 0 → world → camera 1. A marker published by a localization service joins the graph the same way, and `FrameTransformation.<marker>.<camera>` follows it as it moves.

## Reference

The topics, the graph and its routes, the options, telemetry and development are in the service's [README](https://github.com/luizcarloscf/pris/tree/main/services/pris-frame-transformation#readme).
