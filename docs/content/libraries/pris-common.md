# pris-common

`pris-common` holds the code that more than one PRIS service needs and that isn't messaging ([pris-wire](pris-wire.md)) or message schemas ([pris-msgs](pris-msgs.md)): fetching camera calibrations from [pris-calibration-server](../services/pris-calibration-server.md) and frame transformations from [pris-frame-transformation](../services/pris-frame-transformation.md), at startup, and any other request that waits for its reply.

## Camera calibrations

A service that needs calibrations fetches them once, at startup, before it starts consuming anything else. If one is missing it can't work, so it exits, and Kubernetes restarts it until pris-calibration-server answers. The example runs as is, with a broker on `localhost` (`make broker-up` in this repository) and pris-common installed (see the [README](https://github.com/luizcarloscf/pris/tree/main/packages/pris-common#readme)).

In one terminal, a stand-in for pris-calibration-server, which knows camera 2:

```python
from pris_msgs.camera_pb2 import CameraCalibration, GetCalibrationReply, GetCalibrationRequest
from pris_wire.core import Channel
from pris_wire.rpc import ServiceProvider

KNOWN = {2: CameraCalibration(id=2, error=0.4)}


def get_calibration(request, context):
    return GetCalibrationReply(calibrations=[KNOWN[id] for id in request.ids])


channel = Channel("amqp://guest:guest@localhost:5672")
provider = ServiceProvider(channel)
provider.delegate("CalibrationServer.GetCalibration", get_calibration,
                  GetCalibrationRequest, GetCalibrationReply)
provider.run()                                          # serves until interrupted
```

In another, a client that fetches it:

```python
from pris_wire.core import Channel
from pris_common.calibrations import fetch_calibrations

channel = Channel("amqp://guest:guest@localhost:5672")
calibrations = fetch_calibrations(channel, [2])
print(calibrations[2].error)                            # 0.4
channel.close()
```

`fetch_calibrations` raises `RuntimeError` when the server doesn't know a camera or its reply misses one, and `socket.timeout` when no reply arrives within `timeout` (5 s by default). It consumes the channel until the reply arrives and drops anything else, so a service calls it before subscribing to its topics.

## Frame transformations

`fetch_transformations` does the same with pairs of frames, from pris-frame-transformation: each transformation maps the coordinates of its source frame to those of its target frame. The reply holds a transformation as it is now, so it suits fixed ones, such as between a camera and the world; one that changes, such as a marker's, is watched on its `FrameTransformation.<source>.<target>` topic instead. The example also needs pris-msgs' `numpy` extra.

In one terminal, a stand-in for pris-frame-transformation, which knows the transformation from the world (frame 1000) to camera 2:

```python
import numpy as np
from pris_msgs.camera_pb2 import (
    FrameTransformation,
    GetTransformationReply,
    GetTransformationRequest,
)
from pris_msgs.utils.tensor import to_tensor
from pris_wire.core import Channel
from pris_wire.rpc import ServiceProvider

world_to_camera = np.eye(4)
world_to_camera[:3, 3] = [0.0, 0.0, 3.0]                # the camera 3 m away from the world origin
KNOWN = {(1000, 2): FrameTransformation(source=1000, target=2, tf=to_tensor(world_to_camera))}


def get_transformation(request, context):
    pairs = [(pair.source, pair.target) for pair in request.ids]
    return GetTransformationReply(transformations=[KNOWN[pair] for pair in pairs])


channel = Channel("amqp://guest:guest@localhost:5672")
provider = ServiceProvider(channel)
provider.delegate("FrameTransformation.GetTransformation", get_transformation,
                  GetTransformationRequest, GetTransformationReply)
provider.run()                                          # serves until interrupted
```

In another, a client that fetches it:

```python
from pris_msgs.utils.tensor import to_array
from pris_wire.core import Channel
from pris_common.transformations import fetch_transformations

channel = Channel("amqp://guest:guest@localhost:5672")
transformations = fetch_transformations(channel, [(1000, 2)])
print(to_array(transformations[1000, 2].tf)[:3, 3])    # [0. 0. 3.]
channel.close()
```

A pair without a route raises `RuntimeError` naming it, and no reply within `timeout` raises `socket.timeout`.

## Any request

Both functions are built on `pris_common.rpc.call`, which publishes any request and waits for its reply, for other services a component needs to ask once at startup: `reply = call(channel, request, "Service.Method")`, then `reply.unpack(ReplyType)`. An error status raises `RuntimeError`, and no reply within `timeout` raises `socket.timeout`.

## Reference

The details and development are in the package's [README](https://github.com/luizcarloscf/pris/tree/main/packages/pris-common#readme).
