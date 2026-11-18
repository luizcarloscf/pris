# pris-msgs

Every message in PRIS is a [Protocol Buffers](https://protobuf.dev/overview/) message. Its schema is written once, in a `.proto` file. Components agree on the data because they share the schemas, not code. `pris_msgs` holds the schemas every component may use and their generated Python code.

!!! info "New to Protocol Buffers?"

    These pages from the official documentation cover what you need:

    - [Overview](https://protobuf.dev/overview/): what protobuf is and when to use it;
    - [Language guide (proto3)](https://protobuf.dev/programming-guides/proto3/): how to read and write a `.proto` file;
    - [Python tutorial](https://protobuf.dev/getting-started/pythontutorial/) and [Python generated code](https://protobuf.dev/reference/python/python-generated/): using messages from Python;
    - [JSON mapping](https://protobuf.dev/programming-guides/json/): how a message looks as JSON;
    - [Well-known types](https://protobuf.dev/reference/protobuf/google.protobuf/): timestamps, durations and scalar wrappers, which PRIS reuses instead of redefining.

## The schemas

| File | Package | Contents |
|---|---|---|
| `common.proto` | `pris.common` | positions, poses, speeds, tensors, sampling settings |
| `image.proto` | `pris.vision` | images and object or keypoint annotations |
| `camera.proto` | `pris.vision` | camera configuration, calibrations, frame transformations |
| `robot.proto` | `pris.robot` | robot configuration and tasks, range scans |
| `power.proto` | `pris.common` | battery state |

Every message and field is described by the comments of its `.proto` file, in `packages/pris-msgs/src/pris_msgs/`.

## Using messages

Each `.proto` file is a Python module, `pris_msgs.<name>_pb2`:

```python
from pris_msgs.common_pb2 import Pose

pose = Pose()
pose.position.x = 1.5
data = pose.SerializeToString()      # bytes, to send
same = Pose.FromString(data)         # and back
print(same == pose, same.position.x) # True 1.5
```

## Helpers

The `pris_msgs.utils` modules cover what most components do with messages. Each example below runs as is, with `pip install "pris-msgs[numpy,opencv]"`; each function's arguments, return value and errors are in its docstring.

### JSON files

`pris_msgs.utils.io` loads and saves any message as a JSON file, following the [JSON mapping](https://protobuf.dev/programming-guides/json/). Services keep their options this way:

```python
from pris_msgs.common_pb2 import SamplingSettings
from pris_msgs.utils.io import load, save

options = SamplingSettings()
options.frequency.value = 10.0
save("options.json", options)

loaded = load("options.json", SamplingSettings)
print(loaded.frequency.value)                  # 10.0
print(open("options.json").read())             # {"frequency": 10.0}, indented
```

### Tensors

`pris_msgs.utils.tensor` converts a `pris.common.Tensor`, such as a camera's intrinsic matrix, to a NumPy array and back. Needs `pris-msgs[numpy]`.

```python
import numpy as np

from pris_msgs.camera_pb2 import CameraCalibration
from pris_msgs.utils.tensor import to_array, to_tensor

calibration = CameraCalibration()
calibration.intrinsic.CopyFrom(to_tensor(np.array([[800.0, 0, 320], [0, 800, 240], [0, 0, 1]])))
print([dim.name for dim in calibration.intrinsic.shape.dims])   # ['rows', 'cols']

intrinsic = to_array(calibration.intrinsic)
print(intrinsic.shape, intrinsic[0, 2])        # (3, 3) 320.0
```

### Vertices

`pris_msgs.utils.vertex` converts a `pris.vision.Vertex`, a point in an image (x, y) or in space (x, y, z), to a NumPy array and back, optionally in homogeneous coordinates to apply a 3x3 or 4x4 transform. Needs `pris-msgs[numpy]`.

```python
import numpy as np

from pris_msgs.image_pb2 import Vertex
from pris_msgs.utils.vertex import to_array, to_vertex

transform = np.eye(4)
transform[:3, 3] = (1.0, 0.0, 0.5)             # translation

point = transform @ to_array(Vertex(x=1, y=2, z=3), homogeneous=True)
print(point)                                   # [2.  2.  3.5 1. ]
print(to_vertex(point, homogeneous=True))      # x: 2 y: 2 z: 3.5 (one field per line)

pixel = to_array(Vertex(x=320, y=240), dims=2)
print(pixel)                                   # [320. 240.]
```

### Images

`pris_msgs.utils.image` decodes a `pris.vision.Image` (JPEG, PNG or WebP) to a NumPy array of BGR or gray pixels, and encodes arrays back. Needs `pris-msgs[opencv]`.

```python
import numpy as np

from pris_msgs.image_pb2 import ImageFormats
from pris_msgs.utils.image import to_array, to_image

pixels = np.zeros((480, 640, 3), dtype=np.uint8)
pixels[:, :320] = (255, 0, 0)                  # left half blue (BGR)

image = to_image(pixels, ImageFormats.JPEG, compression=0.8)
print(len(image.data) < pixels.nbytes)         # True: encoded

print(to_array(image).shape)                   # (480, 640, 3)
print(to_array(image, gray=True).shape)        # (480, 640)
```

### Annotations

`pris_msgs.utils.annotation` converts the keypoints of a `pris.vision.ObjectAnnotation`, such as a detected person's skeleton, to NumPy arrays in the order of a list of `HumanKeypoints` ids, and back. Needs `pris-msgs[numpy]`.

```python
import numpy as np

from pris_msgs.image_pb2 import HumanKeypoints as K
from pris_msgs.utils.annotation import to_annotation, to_array

ids = [K.NOSE, K.LEFT_EYE, K.RIGHT_EYE]
points = np.array([[320.0, 240.0], [310.0, 230.0], [np.nan, np.nan]])   # right eye not seen
scores = np.array([0.9, 0.8, 0.0])

person = to_annotation(points, scores, ids, label="human_skeleton")
print(len(person.keypoints), round(person.score, 2))   # 2 0.85

points, scores = to_array(person, ids)
print(points)          # (3, 3): x y z per id, NaN for the right eye
```

### Your own schemas

A component with messages of its own can import the shared ones in its `.proto` files and compile them with `pris_msgs.utils.build`, which runs protoc with the installed `pris_msgs/*.proto` on the import path. With `pip install grpcio-tools` for protoc, save this as `proto/my.proto`:

```protobuf
syntax = "proto3";

package my.service;

import "pris_msgs/common.proto";

message MyMessage {
  pris.common.Pose pose = 1;
}
```

```shell
mkdir -p gen
PROTOC="python -m grpc_tools.protoc" python -m pris_msgs.utils.build --proto_path proto --out gen proto/my.proto
cd gen && python -c "from my_pb2 import MyMessage; print(MyMessage(pose={'position': {'x': 1.5}}))"
```

## Reference

Installation and development (`make proto`) are in the package's [README](https://github.com/luizcarloscf/pris/tree/main/packages/pris-msgs#readme).